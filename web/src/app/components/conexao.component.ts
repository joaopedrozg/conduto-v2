import { Component, Input, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Credenciais, Sgbd } from '../services/api.service';
import { ToastService } from '../services/toast.service';
import { DICA_BACKEND_OFF, backendIndisponivel, mensagemErroApi } from '../services/erro-api';

/**
 * Card de conexão (origem ou destino): SGBD atualiza os defaults,
 * bancos e schemas carregam dinamicamente em seletores.
 * O objeto `valor` é compartilhado com o pai (mutação direta).
 */
@Component({
  selector: 'conduto-conexao',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <h3>{{ titulo }}</h3>
    <label>SGBD</label>
    <select [(ngModel)]="valor.tipo" (change)="aoMudarTipo()">
      <option *ngFor="let s of sgbds" [value]="s.tipo">{{ s.nome }}</option>
    </select>
    <label>{{ ehArquivo() ? 'Caminho / URI' : 'Host' }}</label>
    <input [(ngModel)]="valor.host" [placeholder]="placeholderHost()" />
    <label *ngIf="!ehArquivo()">Porta</label>
    <input *ngIf="!ehArquivo()" [(ngModel)]="valor.port" />
    <label>Usuário</label>
    <input [(ngModel)]="valor.user" />
    <label>Senha</label>
    <input type="password" [(ngModel)]="valor.password" />
    <div class="linha">
      <button (click)="testar()">Testar conexão</button>
      <button class="secundario" (click)="carregarBancos()">Carregar bancos</button>
    </div>
    <p class="estado" *ngIf="estado()">{{ estado() }}</p>
    <label *ngIf="bancos().length">Banco</label>
    <select *ngIf="bancos().length" [(ngModel)]="valor.database" (change)="aoEscolherBanco()">
      <option *ngFor="let b of bancos()" [value]="b">{{ b }}</option>
    </select>
    <div class="linha" *ngIf="bancos().length">
      <button class="secundario" (click)="carregarSchemas()">Carregar schemas</button>
    </div>
    <label *ngIf="schemasList().length">Schema</label>
    <select *ngIf="schemasList().length" [(ngModel)]="valor.schema">
      <option *ngFor="let s of schemasList()" [value]="s">{{ s }}</option>
    </select>
    <div class="linha">
      <button class="secundario" (click)="verificarDrivers()">Verificar drivers</button>
      <button class="secundario" (click)="instalarDrivers()">Instalar drivers</button>
      <button class="secundario" *ngIf="valor.tipo === 'sqlserver'" (click)="instalarOdbc()">
        Instalar ODBC
      </button>
    </div>
  `,
  styles: [
    '.linha { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }',
    '.linha button { margin: 4px 0 0; }',
    '.estado { font-size: 0.9em; color: var(--neutro); }',
  ],
})
export class ConexaoComponent {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  @Input() titulo = '';
  @Input() valor!: Credenciais;
  @Input() sgbds: Sgbd[] = [];
  estado = signal('');
  bancos = signal<string[]>([]);
  schemasList = signal<string[]>([]);

  ehArquivo(): boolean {
    return this.valor?.tipo === 'duckdb' || this.valor?.tipo === 'deltalake';
  }

  placeholderHost(): string {
    return this.ehArquivo() ? 'Caminho ou URI (ex: s3://bucket/dados)' : 'Host (ex: localhost)';
  }

  private dizer(msg: string, tipo: 'ok' | 'erro' | 'info' = 'info'): void {
    this.estado.set(msg);
    if (tipo === 'erro') this.toast.erro(`${this.titulo}: ${msg}`);
    else if (tipo === 'ok') this.toast.ok(`${this.titulo}: ${msg}`);
  }

  private falhou(e: unknown, prefixo: string): void {
    this.dizer(backendIndisponivel(e) ? DICA_BACKEND_OFF : `${prefixo}: ${mensagemErroApi(e)}`, 'erro');
  }

  /** Ao trocar o SGBD, preenche os defaults do adapter. */
  aoMudarTipo(): void {
    const s = this.sgbds.find((x) => x.tipo === this.valor.tipo);
    if (!s) return;
    this.valor.host = s.host_padrao;
    this.valor.port = s.porta_padrao;
    this.valor.user = s.usuario_padrao;
    this.valor.database = s.banco_padrao;
    this.valor.schema = '';
    this.bancos.set([]);
    this.schemasList.set([]);
    this.dizer(`Defaults de ${s.nome} aplicados.`);
  }

  testar(): void {
    this.api.testar(this.valor).subscribe({
      next: (r) => {
        this.dizer(r.ok ? 'Conexão OK.' : `Falha: ${r.mensagem}`, r.ok ? 'ok' : 'erro');
        if (r.ok) this.carregarBancos(true);
      },
      error: (e) => this.falhou(e, 'Teste'),
    });
  }

  carregarBancos(silencioso = false): void {
    this.api.bancos(this.valor).subscribe({
      next: (r) => {
        this.bancos.set(r.bancos);
        if (r.bancos.length && !r.bancos.includes(this.valor.database)) {
          this.valor.database = r.bancos[0];
        }
        if (!silencioso) this.dizer(`${r.bancos.length} banco(s) carregado(s).`, 'ok');
        if (r.bancos.length) this.carregarSchemas(true);
      },
      error: (e) => this.falhou(e, 'Bancos'),
    });
  }

  aoEscolherBanco(): void {
    this.valor.schema = '';
    this.carregarSchemas();
  }

  carregarSchemas(silencioso = false): void {
    this.api.schemas(this.valor).subscribe({
      next: (r) => {
        this.schemasList.set(r.schemas);
        if (r.schemas.length && !r.schemas.includes(this.valor.schema)) {
          this.valor.schema = r.schemas[0];
        }
        if (!silencioso) this.dizer(`${r.schemas.length} schema(s) carregado(s).`, 'ok');
      },
      error: (e) => this.falhou(e, 'Schemas'),
    });
  }

  verificarDrivers(): void {
    this.api.driversFaltantes(this.valor.tipo).subscribe({
      next: (r) =>
        this.dizer(
          r.faltantes.length ? `Drivers ausentes: ${r.faltantes.join(', ')}.` : `Drivers de ${r.tipo} OK.`,
          r.faltantes.length ? 'erro' : 'ok',
        ),
      error: (e) => this.falhou(e, 'Drivers'),
    });
  }

  instalarDrivers(): void {
    this.dizer(`Instalando drivers de ${this.valor.tipo} no servidor...`);
    this.api.instalarDrivers(this.valor.tipo).subscribe({
      next: (r) => this.dizer(r.mensagem, 'ok'),
      error: (e) => this.falhou(e, 'Instalação'),
    });
  }

  instalarOdbc(): void {
    this.dizer('Instalando ODBC Driver do SQL Server no servidor...');
    this.api.instalarOdbc().subscribe({
      next: (r) => this.dizer(r.mensagem, 'ok'),
      error: (e) => this.falhou(e, 'ODBC'),
    });
  }
}
