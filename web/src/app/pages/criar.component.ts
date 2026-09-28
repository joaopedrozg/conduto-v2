import { Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, CRON_PRESETS, Credenciais, Sgbd } from '../services/api.service';
import { ConexaoComponent } from '../components/conexao.component';
import { PastaComponent } from '../components/pasta.component';

/**
 * Wizard de criação — experiência enterprise:
 * Início → Conexões → Tabelas → Schedules → Revisão → Servidor.
 */
@Component({
  selector: 'conduto-criar',
  standalone: true,
  imports: [CommonModule, FormsModule, ConexaoComponent, PastaComponent],
  template: `
    <div class="timeline">
      <span *ngFor="let p of passos; let i = index" [class]="classePasso(i)">
        {{ i < etapa() ? '✓' : i === etapa() ? '●' : '○' }} {{ p }}
      </span>
    </div>

    <div class="card" *ngIf="etapa() === 0">
      <h2>Início</h2>
      <label>Nome do projeto</label>
      <input [(ngModel)]="nomeProjeto" placeholder="meu_projeto" />
      <label>Pasta de destino (no servidor)</label>
      <conduto-pasta [(valor)]="projectDir" />
      <div><button (click)="etapa.set(1)">Avançar</button></div>
    </div>

    <div class="card" *ngIf="etapa() === 1">
      <h2>Conexões</h2>
      <div class="cards">
        <section class="conexao"><conduto-conexao [titulo]="'Origem'" [valor]="origem" [sgbds]="sgbds()" [log]="canalLog" /></section>
        <section class="conexao"><conduto-conexao [titulo]="'Destino'" [valor]="destino" [sgbds]="sgbds()" [log]="canalLog" /></section>
      </div>
      <div>
        <button class="secundario" (click)="etapa.set(0)">Voltar</button>
        <button (click)="carregarTabelas(); etapa.set(2)">Avançar</button>
      </div>
    </div>

    <div class="card" *ngIf="etapa() === 2">
      <h2>Tabelas da origem</h2>
      <label><input type="checkbox" [(ngModel)]="gerarAutomatico" /> Gerar a partir do banco (desmarcado = schemas de exemplo)</label>
      <div *ngIf="gerarAutomatico">
      <div class="linha">
        <input [(ngModel)]="filtro" (input)="pagina.set(0)" placeholder="Buscar em todas as tabelas..." style="flex:1" />
        <button class="secundario" (click)="carregarTabelas()">Recarregar</button>
      </div>
      <p class="contagem">{{ filtradas().length }} de {{ tabelasDisponiveis.length }} tabela(s) · {{ tabelasEscolhidas.length }} selecionada(s)</p>
      <table class="tabelas" *ngIf="filtradas().length">
        <thead><tr><th></th><th>Schema</th><th>Tabela</th></tr></thead>
        <tbody>
          <tr *ngFor="let t of paginaAtual()">
            <td><input type="checkbox" [checked]="selecionada(t)" (change)="alternar(t)" /></td>
            <td>{{ t.schema }}</td>
            <td>{{ t.table }}</td>
          </tr>
        </tbody>
      </table>
      <div class="linha" *ngIf="totalPaginas() > 1">
        <button class="secundario" [disabled]="pagina() === 0" (click)="pagina.set(pagina() - 1)">← Anterior</button>
        <span class="contagem">Página {{ pagina() + 1 }} de {{ totalPaginas() }}</span>
        <button class="secundario" [disabled]="pagina() === totalPaginas() - 1" (click)="pagina.set(pagina() + 1)">Próxima →</button>
      </div>
      <div class="linha">
        <button class="secundario" (click)="selecionarVisiveis()">Selecionar visíveis</button>
        <button class="secundario" (click)="tabelasEscolhidas = []">Limpar seleção</button>
      </div>
      </div>
      <div>
        <button class="secundario" (click)="etapa.set(1)">Voltar</button>
        <button (click)="etapa.set(3)">Avançar</button>
      </div>
    </div>

    <div class="card" *ngIf="etapa() === 3">
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
      <div>
        <button class="secundario" (click)="etapa.set(2)">Voltar</button>
        <button (click)="etapa.set(4)">Revisar</button>
      </div>
    </div>

    <div class="card" *ngIf="etapa() === 4">
      <h2>Revisão</h2>
      <p><strong>Projeto:</strong> {{ nomeProjeto }} ({{ projectDir }})</p>
      <p><strong>Origem:</strong> {{ origem.tipo }} &#64; {{ origem.host }}/{{ origem.database }} · schema {{ origem.schema }}</p>
      <p><strong>Destino:</strong> {{ destino.tipo }} &#64; {{ destino.host }}/{{ destino.database }} · schema {{ destino.schema }}</p>
      <p><strong>Tabelas:</strong> {{ tabelasEscolhidas.length }} · <strong>Frequência:</strong> {{ cronFinal() || 'padrão' }}</p>
      <div>
        <button class="secundario" (click)="etapa.set(3)">Voltar</button>
        <button (click)="criar()">Criar projeto</button>
      </div>
    </div>

    <div class="card" *ngIf="etapa() === 5">
      <h2>Servidor Dagster</h2>
      <p><strong>Projeto:</strong> {{ projetoCriado || projectDir }}</p>
      <p class="contagem" *ngIf="dagster().pid">PID {{ dagster().pid }}</p>
      <p *ngIf="dagster().responde">No ar em <a [href]="dagster().url" target="_blank">{{ dagster().url }}</a></p>
      <p *ngIf="dagster().rodando && !dagster().responde">Iniciando... clique em Atualizar em alguns segundos.</p>
      <div class="linha">
        <button (click)="iniciarDagster()" [disabled]="dagster().rodando">Subir servidor</button>
        <button class="secundario" (click)="atualizarDagster()">Atualizar status</button>
        <button class="secundario" (click)="pararDagster()" [disabled]="!dagster().rodando">Parar</button>
        <button class="secundario" (click)="etapa.set(4)">Voltar à revisão</button>
      </div>
    </div>

    <pre class="log" *ngIf="log()">{{ log() }}</pre>
  `,
  styles: [
    '.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }',
    '.conexao { border: 1px solid var(--borda); border-radius: 8px; padding: 12px; }',
    '.linha { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 8px 0; }',
    '.linha button { margin: 0; }',
    '.contagem { color: var(--neutro); font-size: .9em; }',
    'table.tabelas { width: 100%; border-collapse: collapse; margin: 8px 0; }',
    'table.tabelas th, table.tabelas td { border-bottom: 1px solid var(--borda); padding: 6px 8px; text-align: left; }',
    '.freq label { display: block; margin: 4px 0; }',
  ],
})
export class CriarComponent {
  private api = inject(ApiService);
  passos = ['Início', 'Conexões', 'Tabelas', 'Schedules', 'Revisão', 'Servidor'];
  presets = CRON_PRESETS;
  etapa = signal(0);
  log = signal('');
  canalLog = { set: (m: string) => this.log.set(m) };
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
  tabelasDisponiveis: { schema: string; table: string }[] = [];
  tabelasEscolhidas: { schema: string; table: string }[] = [];
  filtro = '';
  pagina = signal(0);
  tamanhoPagina = 10;
  dagster = signal<{ rodando: boolean; responde: boolean; pid: number | null; url: string }>(
    { rodando: false, responde: false, pid: null, url: 'http://localhost:3000' },
  );

  filtradas = computed(() => {
    const f = this.filtro.trim().toLowerCase();
    // A busca percorre a lista completa; a paginação fatia o resultado.
    const todas = this.tabelasDisponiveis.filter(
      (t) => !f || `${t.schema}.${t.table}`.toLowerCase().includes(f),
    );
    return todas;
  });
  totalPaginas = computed(() => Math.max(1, Math.ceil(this.filtradas().length / this.tamanhoPagina)));
  paginaAtual = computed(() => {
    const p = Math.min(this.pagina(), this.totalPaginas() - 1);
    return this.filtradas().slice(p * this.tamanhoPagina, (p + 1) * this.tamanhoPagina);
  });
  cronFinal = computed(() => {
    if (!this.gerarSchedules) return '';
    if (this.freqId === 'custom') return this.cronCustom.trim();
    return this.presets.find((p) => p.id === this.freqId)?.cron ?? '';
  });

  constructor() {
    this.api.sgbds().subscribe((s) => this.sgbds.set(s));
  }

  classePasso(i: number): string {
    return i < this.etapa() ? 'feito' : i === this.etapa() ? 'atual' : '';
  }

  carregarTabelas(): void {
    this.api.tabelas(this.origem).subscribe({
      next: (r) => {
        this.tabelasDisponiveis = r.tabelas;
        this.pagina.set(0);
        this.log.set(`${r.tabelas.length} tabela(s) na origem.`);
      },
      error: (e) => this.log.set(`Sem tabelas: ${e.error?.detail ?? e.message}`),
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
          this.log.set('Projeto criado: ' + JSON.stringify(resp, null, 2));
          this.etapa.set(5);
          this.atualizarDagster();
        },
        error: (e) => this.log.set(`Erro: ${e.error?.detail ?? e.message}`),
      });
  }

  atualizarDagster(): void {
    this.api.dagsterStatus(this.projetoCriado || this.projectDir).subscribe({
      next: (r) => this.dagster.set(r),
      error: (e) => this.log.set(`Dagster: ${e.error?.detail ?? e.message}`),
    });
  }

  iniciarDagster(): void {
    this.log.set('Subindo o servidor Dagster (pode levar ~1 min na primeira vez)...');
    this.api.dagsterIniciar(this.projetoCriado || this.projectDir).subscribe({
      next: (r) => {
        this.dagster.set({ ...r, responde: false });
        this.log.set(`Dagster subindo (PID ${r.pid}). Aguarde e clique em Atualizar status.`);
      },
      error: (e) => this.log.set(`Dagster: ${e.error?.detail ?? e.message}`),
    });
  }

  pararDagster(): void {
    this.api.dagsterParar(this.projetoCriado || this.projectDir).subscribe({
      next: (r) => {
        this.dagster.set({ rodando: r.rodando, responde: false, pid: null, url: 'http://localhost:3000' });
        this.log.set('Servidor Dagster parado.');
      },
      error: (e) => this.log.set(`Dagster: ${e.error?.detail ?? e.message}`),
    });
  }
}
