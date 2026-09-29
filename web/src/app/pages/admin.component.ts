import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ApiService, CRON_PRESETS } from '../services/api.service';
import { CriarComponent } from './criar.component';
import { ToastService } from '../services/toast.service';
import { DICA_BACKEND_OFF, backendIndisponivel, mensagemErroApi } from '../services/erro-api';

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
      <p *ngIf="dagster().responde">No ar em <a [href]="dagster().url" target="_blank">{{ dagster().url }}</a><span *ngIf="dagster().externo"> (externo — subido fora da Web UI)</span></p>
      <p *ngIf="dagster().rodando && !dagster().responde">Iniciando...</p>
      <p *ngIf="!dagster().rodando && !dagster().responde">Parado.</p>
      <button (click)="iniciarDagster()" [disabled]="dagster().rodando || dagster().responde">Subir servidor</button>
      <button class="secundario" (click)="atualizarDagster()">Atualizar status</button>
      <button class="secundario" (click)="pararDagster()" [disabled]="!dagster().rodando">Parar</button>
      <p class="contagem" *ngIf="dagster().externo" style="color: var(--neutro); font-size: .9em">Servidor externo: pare pelo terminal que o subiu.</p>
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
  private toast = inject(ToastService);
  private rota = inject(ActivatedRoute);
  presets = CRON_PRESETS;
  projectDir = '.';
  driverTipo = 'sqlserver';
  cronPreset = '';
  cronCustom = '';
  dagster = signal<{ rodando: boolean; responde: boolean; externo: boolean; pid: number | null; url: string }>(
    { rodando: false, responde: false, externo: false, pid: null, url: 'http://localhost:3000' },
  );
  log = signal('');
  ddl = signal('');

  constructor() {
    // Projeto atual: ?projeto= da URL, senão o contexto guardado pelo wizard.
    // Com projeto definido, já carrega visão geral + status do Dagster.
    const viaUrl = (this.rota.snapshot.queryParamMap.get('projeto') || '').trim();
    const ctx = CriarComponent.lerContexto();
    if (viaUrl) this.projectDir = viaUrl;
    else if (ctx?.dir) this.projectDir = ctx.dir;
    if (viaUrl || ctx?.dir) {
      this.resumo();
      this.atualizarDagster();
    }
  }

  private falhou(e: unknown, prefixo: string): void {
    this.toast.erro(backendIndisponivel(e) ? DICA_BACKEND_OFF : `${prefixo}: ${mensagemErroApi(e)}`);
  }

  resumo(): void {
    this.api.resumo(this.projectDir).subscribe({
      next: (r) => this.log.set(JSON.stringify(r, null, 2)),
      error: (e) => this.falhou(e, 'Visão geral'),
    });
  }

  verDdl(aplicar: boolean): void {
    this.api.ddl(this.projectDir, aplicar).subscribe({
      next: (r) => {
        this.ddl.set(r.ddl);
        this.toast.ok(`${r.comandos} comando(s), ${r.aplicados} aplicado(s).`);
      },
      error: (e) => this.falhou(e, 'DDL'),
    });
  }

  regenerar(): void {
    const cron = this.cronPreset === 'custom' ? this.cronCustom.trim() : this.presetCron(this.cronPreset);
    this.api.schedules(this.projectDir, cron || undefined).subscribe({
      next: (r) => {
        this.log.set(JSON.stringify(r, null, 2));
        this.toast.ok('Schedules regenerados.');
      },
      error: (e) => this.falhou(e, 'Schedules'),
    });
  }

  private presetCron(id: string): string {
    return this.presets.find((p) => p.id === id)?.cron ?? '';
  }

  atualizarDagster(): void {
    this.api.dagsterStatus(this.projectDir).subscribe({
      next: (r) => this.dagster.set(r),
      error: (e) => this.falhou(e, 'Dagster'),
    });
  }

  iniciarDagster(): void {
    this.toast.info('Subindo o servidor Dagster...');
    this.api.dagsterIniciar(this.projectDir).subscribe({
      next: (r) => {
        this.dagster.set({ ...r, responde: false, externo: false });
        this.toast.info(`Dagster subindo (PID ${r.pid}). Aguarde e clique em Atualizar status.`);
      },
      error: (e) => this.falhou(e, 'Dagster'),
    });
  }

  pararDagster(): void {
    this.api.dagsterParar(this.projectDir).subscribe({
      next: (r) => {
        this.dagster.set({ rodando: r.rodando, responde: false, externo: false, pid: null, url: 'http://localhost:3000' });
        this.toast.ok('Servidor Dagster parado.');
      },
      error: (e) => this.falhou(e, 'Dagster'),
    });
  }

  inferir(): void {
    this.api.inferir(this.projectDir).subscribe({
      next: (r) => {
        this.log.set(JSON.stringify(r, null, 2));
        this.toast.ok('Colunas inferidas.');
      },
      error: (e) => this.falhou(e, 'Inferir'),
    });
  }

  verificarDrivers(): void {
    this.api.driversFaltantes(this.driverTipo).subscribe({
      next: (r) => {
        if (r.faltantes.length) this.toast.erro(`Drivers ausentes (${r.tipo}): ${r.faltantes.join(', ')}.`);
        else this.toast.ok(`Drivers de ${r.tipo} OK.`);
      },
      error: (e) => this.falhou(e, 'Drivers'),
    });
  }

  instalarDrivers(): void {
    this.toast.info(`Instalando drivers de ${this.driverTipo} no servidor...`);
    this.api.instalarDrivers(this.driverTipo).subscribe({
      next: (r) => this.toast.ok(r.mensagem),
      error: (e) => this.falhou(e, 'Instalação'),
    });
  }

  verOdbc(): void {
    this.api.odbcStatus().subscribe({
      next: (r) => {
        if (r.ok) this.toast.ok(`ODBC OK: ${r.instalados.join(', ')}`);
        else this.toast.erro('ODBC do SQL Server ausente no servidor.');
      },
      error: (e) => this.falhou(e, 'ODBC'),
    });
  }

  instalarOdbc(): void {
    this.toast.info('Instalando ODBC Driver do SQL Server no servidor...');
    this.api.instalarOdbc().subscribe({
      next: (r) => this.toast.ok(r.mensagem),
      error: (e) => this.falhou(e, 'ODBC'),
    });
  }
}
