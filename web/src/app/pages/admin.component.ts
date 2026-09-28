import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, CRON_PRESETS } from '../services/api.service';

/**
 * Administração — espelha PASSOS_ADMIN da TUI:
 * visão geral → conexões → ddl → schedules → inferir → servidores/docs.
 */
@Component({
  selector: 'conduto-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="timeline">
      <span class="atual">● Administrar {{ projectDir }}</span>
    </div>
    <div class="card">
      <label>Diretório do projeto</label>
      <input [(ngModel)]="projectDir" />
      <button (click)="resumo()">Visão geral</button>
      <button (click)="verDdl(false)">Gerar DDL</button>
      <button (click)="verDdl(true)">Aplicar DDL</button>
      <button (click)="inferir()">Inferir colunas</button>
    </div>
    <div class="card">
      <h2>Schedules</h2>
      <label>Frequência (vazio = mantém)</label>
      <select [(ngModel)]="cronPreset">
        <option value="">Manter atual</option>
        <option *ngFor="let f of presets" [value]="f.id">{{ f.rotulo }}</option>
      </select>
      <input *ngIf="cronPreset === 'custom'" [(ngModel)]="cronCustom" placeholder="Ex.: 30 8 * * 1-5" />
      <div>
        <button (click)="regenerar()">Regenerar schedules</button>
      </div>
    </div>
    <div class="card">
      <h2>Servidor Dagster</h2>
      <p *ngIf="dagster().responde">No ar em <a [href]="dagster().url" target="_blank">{{ dagster().url }}</a></p>
      <p *ngIf="dagster().rodando && !dagster().responde">Iniciando...</p>
      <p *ngIf="!dagster().rodando">Parado.</p>
      <button (click)="iniciarDagster()" [disabled]="dagster().rodando">Subir servidor</button>
      <button class="secundario" (click)="atualizarDagster()">Atualizar status</button>
      <button class="secundario" (click)="pararDagster()" [disabled]="!dagster().rodando">Parar</button>
    </div>
    <div class="card">
      <h2>Drivers</h2>
      <label>SGBD</label>
      <select [(ngModel)]="driverTipo">
        <option value="postgresql">PostgreSQL</option>
        <option value="mysql">MySQL</option>
        <option value="sqlserver">SQL Server</option>
        <option value="clickhouse">ClickHouse</option>
        <option value="duckdb">DuckDB</option>
        <option value="deltalake">Delta Lake</option>
      </select>
      <button (click)="verificarDrivers()">Verificar drivers</button>
      <button (click)="instalarDrivers()">Instalar drivers (pip no servidor)</button>
      <button class="secundario" (click)="verOdbc()">Status ODBC SQL Server</button>
      <button class="secundario" (click)="instalarOdbc()">Instalar ODBC SQL Server</button>
    </div>
    <pre class="log" *ngIf="log()">{{ log() }}</pre>
    <pre class="log" *ngIf="ddl()">{{ ddl() }}</pre>
  `,
})
export class AdminComponent {
  private api = inject(ApiService);
  presets = CRON_PRESETS;
  projectDir = '.';
  driverTipo = 'sqlserver';
  cronPreset = '';
  cronCustom = '';
  dagster = signal<{ rodando: boolean; responde: boolean; pid: number | null; url: string }>(
    { rodando: false, responde: false, pid: null, url: 'http://localhost:3000' },
  );
  log = signal('');
  ddl = signal('');

  resumo(): void {
    this.api.resumo(this.projectDir).subscribe({
      next: (r) => this.log.set(JSON.stringify(r, null, 2)),
      error: (e) => this.log.set(`Erro: ${e.error?.detail ?? e.message}`),
    });
  }

  verDdl(aplicar: boolean): void {
    this.api.ddl(this.projectDir, aplicar).subscribe({
      next: (r) => {
        this.ddl.set(r.ddl);
        this.log.set(`${r.comandos} comando(s), ${r.aplicados} aplicado(s).`);
      },
      error: (e) => this.log.set(`Erro: ${e.error?.detail ?? e.message}`),
    });
  }

  regenerar(): void {
    const cron = this.cronPreset === 'custom' ? this.cronCustom.trim() : this.presetCron(this.cronPreset);
    this.api.schedules(this.projectDir, cron || undefined).subscribe({
      next: (r) => this.log.set(JSON.stringify(r, null, 2)),
      error: (e) => this.log.set(`Erro: ${e.error?.detail ?? e.message}`),
    });
  }

  private presetCron(id: string): string {
    return this.presets.find((p) => p.id === id)?.cron ?? '';
  }

  atualizarDagster(): void {
    this.api.dagsterStatus(this.projectDir).subscribe({
      next: (r) => this.dagster.set(r),
      error: (e) => this.log.set(`Dagster: ${e.error?.detail ?? e.message}`),
    });
  }

  iniciarDagster(): void {
    this.log.set('Subindo o servidor Dagster...');
    this.api.dagsterIniciar(this.projectDir).subscribe({
      next: (r) => {
        this.dagster.set({ ...r, responde: false });
        this.log.set(`Dagster subindo (PID ${r.pid}). Aguarde e clique em Atualizar status.`);
      },
      error: (e) => this.log.set(`Dagster: ${e.error?.detail ?? e.message}`),
    });
  }

  pararDagster(): void {
    this.api.dagsterParar(this.projectDir).subscribe({
      next: (r) => {
        this.dagster.set({ rodando: r.rodando, responde: false, pid: null, url: 'http://localhost:3000' });
        this.log.set('Servidor Dagster parado.');
      },
      error: (e) => this.log.set(`Dagster: ${e.error?.detail ?? e.message}`),
    });
  }

  inferir(): void {
    this.api.inferir(this.projectDir).subscribe({
      next: (r) => this.log.set(JSON.stringify(r, null, 2)),
      error: (e) => this.log.set(`Erro: ${e.error?.detail ?? e.message}`),
    });
  }

  verificarDrivers(): void {
    this.api.driversFaltantes(this.driverTipo).subscribe({
      next: (r) =>
        this.log.set(
          r.faltantes.length
            ? `Drivers ausentes (${r.tipo}): ${r.faltantes.join(', ')}.`
            : `Drivers de ${r.tipo} OK.`,
        ),
      error: (e) => this.log.set(`Erro: ${e.error?.detail ?? e.message}`),
    });
  }

  instalarDrivers(): void {
    this.log.set(`Instalando drivers de ${this.driverTipo} no servidor...`);
    this.api.instalarDrivers(this.driverTipo).subscribe({
      next: (r) => this.log.set(r.mensagem),
      error: (e) => this.log.set(`Falha ao instalar: ${e.error?.detail ?? e.message}`),
    });
  }

  verOdbc(): void {
    this.api.odbcStatus().subscribe({
      next: (r) => this.log.set(r.ok ? `ODBC OK: ${r.instalados.join(', ')}` : 'ODBC do SQL Server ausente no servidor.'),
      error: (e) => this.log.set(`Erro: ${e.error?.detail ?? e.message}`),
    });
  }

  instalarOdbc(): void {
    this.log.set('Instalando ODBC Driver do SQL Server no servidor...');
    this.api.instalarOdbc().subscribe({
      next: (r) => this.log.set(r.mensagem),
      error: (e) => this.log.set(`Falha no ODBC: ${e.error?.detail ?? e.message}`),
    });
  }
}
