import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, ConexaoSalva, Credenciais, Sgbd } from '../services/api.service';
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
    <div class="linha" *ngIf="escolherSchema && bancos().length">
      <button type="button" class="secundario" (click)="carregarSchemas()">Carregar schemas</button>
    </div>
    <label *ngIf="escolherSchema && schemasList().length">Schema</label>
    <select *ngIf="escolherSchema && schemasList().length" [(ngModel)]="valor.schema">
      <option *ngFor="let s of schemasList()" [value]="s">{{ s }}</option>
    </select>
    <div class="linha">
      <button type="button" class="secundario" (click)="verificarDrivers()">Verificar drivers</button>
      <button type="button" class="secundario" (click)="instalarDrivers()">Instalar drivers</button>
      <button type="button" class="secundario" *ngIf="valor.tipo === 'sqlserver'" (click)="instalarOdbc()">
        Instalar ODBC
      </button>
    </div>
    <div *ngIf="salvas">
      <h4>Conexões salvas</h4>
      <div class="linha">
        <input [(ngModel)]="apelido" placeholder="Nome (ex.: produção)" style="flex:1" />
        <button type="button" class="secundario" (click)="salvarAtual()">Salvar atual</button>
      </div>
      <table class="dados" *ngIf="salvasLista().length">
        <thead><tr><th>Nome</th><th>SGBD</th><th>Host</th><th>Banco</th><th>Usuário</th><th></th></tr></thead>
        <tbody>
          <tr *ngFor="let s of salvasLista()" class="clicavel" (click)="usarSalva(s)" title="Clique para usar">
            <td>{{ s.apelido }}</td>
            <td>{{ s.credenciais.tipo }}</td>
            <td>{{ s.credenciais.host }}</td>
            <td>{{ s.credenciais.database }}</td>
            <td>{{ s.credenciais.user }}</td>
            <td class="acoes"><button type="button" class="perigo" (click)="excluirSalva(s, $event)">Excluir</button></td>
          </tr>
        </tbody>
      </table>
      <p class="contagem" *ngIf="!salvasLista().length">Nenhuma salva — preencha e clique em Salvar atual.</p>
    </div>
  `,
  styles: [
    '.linha { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }',
    '.linha button { margin: 4px 0 0; }',
    '.estado { font-size: 0.9em; color: var(--neutro); }',
    'h4 { margin: 14px 0 6px; }',
  ],
})
export class ConexaoComponent implements OnInit {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  @Input() titulo = '';
  @Input() valor!: Credenciais;
  @Input() sgbds: Sgbd[] = [];
  /** false na origem: o schema é escolhido no passo Tabelas, não aqui. */
  @Input() escolherSchema = true;
  /** Tabela de conexões salvas (só na origem, por enquanto). */
  @Input() salvas = true;
  estado = signal('');
  bancos = signal<string[]>([]);
  schemasList = signal<string[]>([]);
  salvasLista = signal<ConexaoSalva[]>([]);
  apelido = '';

  ngOnInit(): void {
    if (this.salvas) this.carregarSalvas();
  }

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
        if (this.escolherSchema && r.bancos.length) this.carregarSchemas(true);
      },
      error: (e) => this.falhou(e, 'Bancos'),
    });
  }

  aoEscolherBanco(): void {
    if (!this.escolherSchema) return;
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

  carregarSalvas(): void {
    this.api.conexoesSalvas().subscribe({
      next: (r) => this.salvasLista.set(r.conexoes),
      error: (e) => this.falhou(e, 'Salvas'),
    });
  }

  salvarAtual(): void {
    this.api.salvarConexao(this.apelido.trim(), this.valor).subscribe({
      next: (s) => {
        this.apelido = '';
        this.carregarSalvas();
        this.toast.ok(`Conexão '${s.apelido}' salva.`);
      },
      error: (e) => this.falhou(e, 'Salvar'),
    });
  }

  usarSalva(s: ConexaoSalva): void {
    Object.assign(this.valor, { ...s.credenciais });
    this.bancos.set([]);
    this.schemasList.set([]);
    this.dizer(`Usando '${s.apelido}' — confira e teste.`, 'info');
  }

  excluirSalva(s: ConexaoSalva, evento: Event): void {
    evento.stopPropagation();
    this.api.excluirConexao(s.id).subscribe({
      next: () => {
        this.carregarSalvas();
        this.toast.ok(`Conexão '${s.apelido}' excluída.`);
      },
      error: (e) => this.falhou(e, 'Excluir'),
    });
  }
}
