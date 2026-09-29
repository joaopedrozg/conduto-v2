import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ApiService, CRON_PRESETS, Credenciais, Sgbd } from '../services/api.service';
import { ToastService } from '../services/toast.service';
import { DICA_BACKEND_OFF, backendIndisponivel, mensagemErroApi } from '../services/erro-api';
import { ConexaoComponent } from '../components/conexao.component';

/**
 * Wizard de criação — experiência enterprise:
 * Início → Conexões → Tabelas → Schedules → Revisão → Servidor.
 */
@Component({
  selector: 'conduto-criar',
  standalone: true,
  imports: [CommonModule, FormsModule, ConexaoComponent],
  template: `
    <div class="timeline">
      <button
        type="button"
        *ngFor="let p of passos; let i = index"
        [class]="classePasso(i)"
        (click)="irPara(i)"
        [title]="i === etapa() ? 'Etapa atual' : 'Ir para ' + p"
      >{{ i < etapa() ? '✓' : i === etapa() ? '●' : '○' }} {{ p }}</button>
    </div>

    <div class="card" *ngIf="etapa() === 0">
      <h2>Conexões</h2>
      <div class="cards">
        <section class="conexao"><conduto-conexao [titulo]="'Origem'" [valor]="origem" [sgbds]="sgbds()" [escolherSchema]="false" /></section>
        <section class="conexao"><conduto-conexao [titulo]="'Destino'" [valor]="destino" [sgbds]="sgbds()" [salvas]="false" /></section>
      </div>
    </div>

    <div class="card" *ngIf="etapa() === 1">
      <h2>Tabelas da origem</h2>
      <label><input type="checkbox" [(ngModel)]="gerarAutomatico" /> Gerar a partir do banco (desmarcado = schemas de exemplo)</label>
      <div *ngIf="gerarAutomatico">
      <div class="linha">
        <span class="contagem">Schemas:</span>
        <button type="button" class="secundario" (click)="todosSchemas()">Todos</button>
        <button type="button" class="secundario" (click)="schemasEscolhidos.set([]); pagina.set(0)">Limpar</button>
      </div>
      <div class="schemas">
        <label *ngFor="let s of schemasDisponiveis()">
          <input type="checkbox" [checked]="schemasEscolhidos().includes(s.schema)" (change)="alternarSchema(s.schema)" />
          {{ s.schema }} ({{ s.qtd }})
        </label>
      </div>
      <div class="linha">
        <span class="contagem">Tabelas:</span>
        <button type="button" class="secundario" (click)="selecionarVisiveis()">Selecionar visíveis</button>
        <button type="button" class="secundario" (click)="tabelasEscolhidas = []">Limpar seleção</button>
      </div>
      <div class="linha">
        <input [ngModel]="filtro()" (ngModelChange)="atualizarFiltro($event)" placeholder="Buscar nas tabelas dos schemas selecionados..." style="flex:1" />
        <button type="button" class="secundario" (click)="carregarTabelas()">Recarregar</button>
        <button type="button" class="secundario" (click)="carregarTabelas(true)">Trazer tudo</button>
      </div>
      <p class="contagem">{{ filtradas().length }} de {{ tabelasDisponiveis().length }} tabela(s) · {{ tabelasEscolhidas.length }} selecionada(s)</p>
      <table class="dados" *ngIf="filtradas().length">
        <thead><tr><th></th><th>Schema</th><th>Tabela</th></tr></thead>
        <tbody>
          <tr *ngFor="let t of paginaAtual()">
            <td><input type="checkbox" [checked]="selecionada(t)" (change)="alternar(t)" /></td>
            <td>{{ t.schema }}</td>
            <td>{{ t.table }}</td>
          </tr>
        </tbody>
      </table>
      <div class="paginacao" *ngIf="totalPaginas() > 1">
        <button type="button" class="secundario" [disabled]="pagina() === 0" (click)="pagina.set(pagina() - 1)">← Anterior</button>
        <span class="contagem">Página {{ pagina() + 1 }} de {{ totalPaginas() }}</span>
        <button type="button" class="secundario" [disabled]="pagina() === totalPaginas() - 1" (click)="pagina.set(pagina() + 1)">Próxima →</button>
      </div>
      </div>
    </div>

    <div class="card" *ngIf="etapa() === 2">
      <h2>Schedules</h2>
      <label><input type="checkbox" [(ngModel)]="gerarSchedules" /> Gerar schedules + código Dagster</label>
      <div *ngIf="gerarSchedules">
        <label>Frequência das cargas</label>
        <div class="freq" *ngFor="let f of presets">
          <label><input type="radio" name="freq" [value]="f.id" [(ngModel)]="freqId" /> {{ f.rotulo }} <code>{{ f.cron }}</code></label>
        </div>
        <input *ngIf="freqId === 'custom'" [(ngModel)]="cronCustom" placeholder="Ex.: 30 8 * * 1-5" />
        <p class="contagem">Cron aplicado: <code>{{ cronFinal() || '(padrão hora em hora)' }}</code></p>
      </div>
      <label><input type="checkbox" [(ngModel)]="aplicarDdl" /> Aplicar DDL no destino ao criar</label>
    </div>

    <div class="card" *ngIf="etapa() === 3">
      <h2>Revisão</h2>
      <p><strong>Projeto:</strong> {{ nomeProjeto }} ({{ projectDir }})</p>
      <p><strong>Origem:</strong> {{ origem.tipo }} &#64; {{ origem.host }}/{{ origem.database }} · schema {{ origem.schema }}</p>
      <p><strong>Destino:</strong> {{ destino.tipo }} &#64; {{ destino.host }}/{{ destino.database }} · schema {{ destino.schema }}</p>
      <p><strong>Tabelas:</strong> {{ tabelasEscolhidas.length }} · <strong>Frequência:</strong> {{ cronFinal() || 'padrão' }}</p>
      <div>
        <button (click)="criar()">Criar projeto</button>
      </div>
    </div>

    <div class="card" *ngIf="etapa() === 4">
      <h2>Servidor Dagster</h2>
      <p><strong>Projeto:</strong> {{ projetoCriado || projectDir }}</p>
      <p class="contagem" *ngIf="dagster().pid">PID {{ dagster().pid }} (gerenciado pela Web UI)</p>
      <p *ngIf="dagster().responde">No ar em <a [href]="dagster().url" target="_blank">{{ dagster().url }}</a><span *ngIf="dagster().externo"> (externo — subido fora da Web UI)</span></p>
      <p *ngIf="dagster().rodando && !dagster().responde">Iniciando... clique em Atualizar em alguns segundos.</p>
      <p *ngIf="!dagster().rodando && !dagster().responde">Parado.</p>
      <div class="linha">
        <button (click)="iniciarDagster()" [disabled]="dagster().rodando || dagster().responde">Subir servidor</button>
        <button class="secundario" (click)="atualizarDagster()">Atualizar status</button>
        <button class="secundario" (click)="pararDagster()" [disabled]="!dagster().rodando">Parar</button>
      </div>
      <p class="contagem" *ngIf="dagster().externo">Servidor externo: pare pelo terminal que o subiu.</p>
    </div>

    <pre class="log" *ngIf="log()">{{ log() }}</pre>
  `,
  styles: [
    '.timeline button { flex: 1; background: none; border: 0; border-top: 3px solid transparent; margin: 0; padding: 10px 4px; font: inherit; font-size: 0.9em; color: var(--neutro); cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }',
    '.timeline button + button { border-left: 1px solid var(--borda); }',
    '.timeline button.feito { color: var(--ok); border-top-color: var(--ok); }',
    '.timeline button.atual { color: var(--info); border-top-color: var(--info); font-weight: 700; }',
    '.timeline button:hover { background: var(--fundo); filter: none; }',
    '.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }',
    '.conexao { border: 1px solid var(--borda); border-radius: 8px; padding: 16px; background: #fff; }',
    '.linha { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 8px 0; }',
    '.linha button { margin: 0; }',
    '.paginacao { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin: 8px 0; }',
    '.paginacao button { margin: 0; }',
    '.contagem { color: var(--neutro); font-size: .9em; }',
    '.schemas { display: flex; gap: 8px 16px; flex-wrap: wrap; margin: 4px 0 8px; }',
    '.schemas label { display: inline-flex; gap: 4px; align-items: center; margin: 0; font-weight: 400; }',
    '.freq label { display: block; margin: 4px 0; }',
  ],
})
export class CriarComponent {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  private rota = inject(ActivatedRoute);
  passos = ['Conexões', 'Tabelas', 'Schedules', 'Revisão', 'Servidor'];
  presets = CRON_PRESETS;
  etapa = signal(0);
  log = signal('');
  sgbds = signal<Sgbd[]>([]);
  nomeProjeto = 'meu_projeto';
  projectDir = './meu_projeto';
  projetoCriado = '';
  origem: Credenciais = { tipo: 'postgresql', host: 'localhost', port: '5432', user: 'postgres', password: 'postgres', database: 'postgres', schema: 'public' };
  destino: Credenciais = { tipo: 'postgresql', host: 'localhost', port: '5432', user: 'postgres', password: 'postgres', database: 'postgres', schema: 'public' };
  gerarAutomatico = true;
  gerarSchedules = true;
  aplicarDdl = false;
  freqId = 'hora';
  cronCustom = '';
  tabelasDisponiveis = signal<{ schema: string; table: string }[]>([]);
  tabelasEscolhidas: { schema: string; table: string }[] = [];
  filtro = signal('');
  pagina = signal(0);
  tamanhoPagina = 10;
  dagster = signal<{ rodando: boolean; responde: boolean; externo: boolean; pid: number | null; url: string }>(
    { rodando: false, responde: false, externo: false, pid: null, url: 'http://localhost:3000' },
  );

  filtradas = computed(() => {
    const f = this.filtro().trim().toLowerCase();
    const schemas = new Set(this.schemasEscolhidos());
    // Só tabelas dos schemas selecionados; a busca refina esse conjunto.
    return this.tabelasDisponiveis().filter(
      (t) =>
        schemas.has(t.schema) &&
        (!f || `${t.schema}.${t.table}`.toLowerCase().includes(f)),
    );
  });
  totalPaginas = computed(() => Math.max(1, Math.ceil(this.filtradas().length / this.tamanhoPagina)));
  paginaAtual = computed(() => {
    const p = Math.min(this.pagina(), this.totalPaginas() - 1);
    return this.filtradas().slice(p * this.tamanhoPagina, (p + 1) * this.tamanhoPagina);
  });

  /** Cron efetivo (método, não computed: lê checkboxes comuns sempre frescos). */
  cronFinal(): string {
    if (!this.gerarSchedules) return '';
    if (this.freqId === 'custom') return this.cronCustom.trim();
    return this.presets.find((p) => p.id === this.freqId)?.cron ?? '';
  }

  atualizarFiltro(valor: string): void {
    this.filtro.set(valor);
    this.pagina.set(0);
  }

  schemasDisponiveis = computed(() => {
    const contagem = new Map<string, number>();
    for (const t of this.tabelasDisponiveis()) contagem.set(t.schema, (contagem.get(t.schema) ?? 0) + 1);
    return [...contagem.entries()]
      .map(([schema, qtd]) => ({ schema, qtd }))
      .sort((a, b) => a.schema.localeCompare(b.schema));
  });
  schemasEscolhidos = signal<string[]>([]);

  alternarSchema(schema: string): void {
    const atual = this.schemasEscolhidos();
    this.schemasEscolhidos.set(
      atual.includes(schema) ? atual.filter((s) => s !== schema) : [...atual, schema],
    );
    this.pagina.set(0);
  }

  todosSchemas(): void {
    this.schemasEscolhidos.set(this.schemasDisponiveis().map((s) => s.schema));
    this.pagina.set(0);
  }

  constructor() {
    this.api.sgbds().subscribe((s) => this.sgbds.set(s));
    // Contexto do `conduto init nome --web`: o projeto já vem decidido
    // na URL (o wizard começa direto nas Conexões, sem etapa Início).
    const params = this.rota.snapshot.queryParamMap;
    const nome = (params.get('nome') || '').trim();
    const dir = (params.get('dir') || '').trim();
    if (nome) {
      this.nomeProjeto = nome;
      this.projectDir = dir || `./${nome}`;
      this.guardarContexto();
    }
  }

  private guardarContexto(): void {
    try {
      localStorage.setItem(
        'conduto.projeto',
        JSON.stringify({ nome: this.nomeProjeto, dir: this.projectDir }),
      );
    } catch {
      /* navegação privada: segue sem persistir */
    }
  }

  static lerContexto(): { nome: string; dir: string } | null {
    try {
      const raw = localStorage.getItem('conduto.projeto');
      if (!raw) return null;
      const ctx = JSON.parse(raw);
      if (typeof ctx?.dir === 'string' && ctx.dir) {
        return { nome: String(ctx.nome ?? ''), dir: ctx.dir };
      }
    } catch {
      /* ignora contexto corrompido */
    }
    return null;
  }

  classePasso(i: number): string {
    return i < this.etapa() ? 'feito' : i === this.etapa() ? 'atual' : '';
  }

  /** Navega pelo clique nos steps; ao entrar em Tabelas carrega se preciso. */
  irPara(i: number): void {
    const alvo = Math.max(0, Math.min(i, this.passos.length - 1));
    this.etapa.set(alvo);
    if (alvo === 1) {
      const chave = this.origemChave(this.origem);
      if (!this.tabelasDisponiveis().length || chave !== this.ultimaOrigem) {
        this.carregarTabelas();
      }
    }
  }

  private origemChave(c: Credenciais): string {
    return [c.tipo, c.host, c.port, c.user, c.database].join('|');
  }
  private ultimaOrigem = '';

  private falhou(e: unknown, prefixo: string): void {
    this.toast.erro(backendIndisponivel(e) ? DICA_BACKEND_OFF : `${prefixo}: ${mensagemErroApi(e)}`);
  }

  carregarTabelas(completo = false): void {
    // Refinando (Recarregar com schemas desmarcados): o backend já traz só
    // os selecionados. Primeira carga ou "Trazer tudo": tudo, depois marca todos.
    const refinando = this.tabelasDisponiveis().length > 0 && !completo;
    const filtroSchemas = refinando ? this.schemasEscolhidos() : [];
    this.api.tabelas(this.origem, filtroSchemas).subscribe({
      next: (r) => {
        this.tabelasDisponiveis.set(r.tabelas);
        this.ultimaOrigem = this.origemChave(this.origem);
        const todos = [...new Set(r.tabelas.map((t) => t.schema))].sort();
        const mantidos = this.schemasEscolhidos().filter((s) => todos.includes(s));
        this.schemasEscolhidos.set(mantidos.length && refinando ? mantidos : todos);
        this.tabelasEscolhidas = [];
        this.pagina.set(0);
        this.toast.ok(`${r.tabelas.length} tabela(s) na origem.`);
      },
      error: (e) => this.falhou(e, 'Tabelas'),
    });
  }

  selecionada(t: { schema: string; table: string }): boolean {
    return this.tabelasEscolhidas.some((x) => x.schema === t.schema && x.table === t.table);
  }

  alternar(t: { schema: string; table: string }): void {
    this.tabelasEscolhidas = this.selecionada(t)
      ? this.tabelasEscolhidas.filter((x) => !(x.schema === t.schema && x.table === t.table))
      : [...this.tabelasEscolhidas, t];
  }

  selecionarVisiveis(): void {
    const atual = new Map(this.tabelasEscolhidas.map((t) => [`${t.schema}.${t.table}`, t]));
    for (const t of this.paginaAtual()) atual.set(`${t.schema}.${t.table}`, t);
    this.tabelasEscolhidas = [...atual.values()];
  }

  criar(): void {
    this.api
      .criarProjeto({
        project_dir: this.projectDir,
        nome_projeto: this.nomeProjeto,
        origem: this.origem,
        destino: this.destino,
        gerar_automatico: this.gerarAutomatico,
        tabelas: this.tabelasEscolhidas,
        gerar_schedules: this.gerarSchedules,
        aplicar_ddl: this.aplicarDdl,
        armazenamento: 'env',
        cron_padrao: this.cronFinal() || null,
      })
      .subscribe({
        next: (r: object) => {
          const resp = r as Record<string, unknown>;
          this.projetoCriado = String(resp['project_dir'] ?? this.projectDir);
          this.projectDir = this.projetoCriado;
          this.guardarContexto();
          this.log.set('Projeto criado: ' + JSON.stringify(resp, null, 2));
          this.toast.ok(`Projeto criado em ${this.projetoCriado}.`);
          this.etapa.set(4);
          this.atualizarDagster();
        },
        error: (e) => this.falhou(e, 'Criar projeto'),
      });
  }

  atualizarDagster(): void {
    this.api.dagsterStatus(this.projetoCriado || this.projectDir).subscribe({
      next: (r) => this.dagster.set(r),
      error: (e) => this.falhou(e, 'Dagster'),
    });
  }

  iniciarDagster(): void {
    this.toast.info('Subindo o servidor Dagster (pode levar ~1 min na primeira vez)...');
    this.api.dagsterIniciar(this.projetoCriado || this.projectDir).subscribe({
      next: (r) => {
        this.dagster.set({ ...r, responde: false, externo: false });
        this.toast.info(`Dagster subindo (PID ${r.pid}). Aguarde e clique em Atualizar status.`);
      },
      error: (e) => this.falhou(e, 'Dagster'),
    });
  }

  pararDagster(): void {
    this.api.dagsterParar(this.projetoCriado || this.projectDir).subscribe({
      next: (r) => {
        this.dagster.set({ rodando: r.rodando, responde: false, externo: false, pid: null, url: 'http://localhost:3000' });
        this.toast.ok('Servidor Dagster parado.');
      },
      error: (e) => this.falhou(e, 'Dagster'),
    });
  }
}
