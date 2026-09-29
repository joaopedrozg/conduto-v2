import { Component, EventEmitter, Input, Output, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api.service';

interface PastaResp {
  atual: string;
  pai: string | null;
  pastas: string[];
  casa: string;
  servidor_cwd: string;
}

/**
 * Seletor da pasta do projeto. Navega as pastas do SERVIDOR (onde o
 * `conduto web` roda e o projeto será criado) — um diálogo nativo do
 * navegador não serviria, pois ele só enxerga a máquina do browser.
 */
@Component({
  selector: 'conduto-pasta',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="pasta-linha">
      <input [(ngModel)]="valor" placeholder="./meu_projeto" style="flex:1" />
      <button type="button" class="secundario" (click)="abrir()">Procurar...</button>
    </div>
    <div class="modal-fundo" *ngIf="aberto()">
      <div class="modal">
        <h3>Onde criar o projeto?</h3>
        <p class="ajuda">Pastas do servidor (onde o <code>conduto web</code> está rodando).</p>
        <div class="atalhos">
          <button type="button" class="secundario" (click)="navegar(casa())">🏠 Início</button>
          <button type="button" class="secundario" (click)="navegar(cwd())">📍 Pasta do backend</button>
          <button type="button" class="secundario" *ngIf="pai()" (click)="navegar(pai()!)">⬆ Voltar</button>
        </div>
        <nav class="migalhas">
          <button type="button" *ngFor="let m of migalhas(); let ultimo = last" [disabled]="ultimo" (click)="navegar(m.caminho)">{{ m.nome }}</button>
        </nav>
        <div class="lista">
          <button type="button" class="pasta" *ngFor="let p of pastas()" (click)="navegar(atual() + '/' + p)">
            📁 {{ p }}
          </button>
          <p class="contagem" *ngIf="!pastas().length">Sem subpastas aqui.</p>
        </div>
        <p class="erro" *ngIf="erro()">{{ erro() }}</p>
        <label>Criar subpasta (opcional)</label>
        <input [(ngModel)]="novaPasta" (input)="limparNome()" placeholder="meu_projeto" />
        <p class="destino">Projeto será criado em:<br /><code>{{ destinoFinal() }}</code></p>
        <div class="acoes">
          <button type="button" class="secundario" (click)="aberto.set(false)">Cancelar</button>
          <button type="button" (click)="confirmar()">Usar esta pasta</button>
        </div>
      </div>
    </div>
  `,
  styles: [
    '.pasta-linha { display: flex; gap: 8px; }',
    '.modal-fundo { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 10; }',
    '.modal { background: #fff; border-radius: 10px; padding: 20px; width: min(600px, 92vw); max-height: 84vh; overflow: auto; }',
    '.ajuda { color: var(--neutro); font-size: .9em; margin-top: -8px; }',
    '.atalhos { display: flex; gap: 8px; flex-wrap: wrap; margin: 8px 0; }',
    '.atalhos button { margin: 0; }',
    '.migalhas { display: flex; gap: 2px; flex-wrap: wrap; margin: 4px 0; }',
    '.migalhas button { background: none; border: 0; color: var(--info); cursor: pointer; padding: 2px 4px; margin: 0; font-size: .85em; }',
    '.migalhas button:disabled { color: var(--neutro); cursor: default; font-weight: bold; }',
    '.lista { display: flex; flex-direction: column; gap: 4px; max-height: 240px; overflow: auto; margin: 8px 0; border: 1px solid var(--borda); border-radius: 6px; padding: 6px; }',
    'button.pasta { background: none; border: 0; color: var(--info); text-align: left; padding: 6px; cursor: pointer; margin: 0; }',
    'button.pasta:hover { background: var(--fundo); }',
    '.contagem { color: var(--neutro); font-size: .9em; }',
    '.erro { color: var(--erro); }',
    '.destino { font-size: .9em; }',
    '.destino code { word-break: break-all; }',
    '.acoes { display: flex; gap: 8px; justify-content: flex-end; margin-top: 8px; }',
    '.acoes button { margin: 0; }',
  ],
})
export class PastaComponent {
  private api = inject(ApiService);
  @Input() valor = './meu_projeto';
  @Output() valorChange = new EventEmitter<string>();
  aberto = signal(false);
  atual = signal('');
  pai = signal<string | null>(null);
  pastas = signal<string[]>([]);
  casa = signal('');
  cwd = signal('');
  erro = signal('');
  novaPasta = '';

  migalhas = computed(() => {
    const partes = this.atual().split(/[/\\]+/).filter(Boolean);
    const raiz = /^[A-Za-z]:$/.test(partes[0] ?? '') ? '' : '/';
    return partes.map((nome, i) => ({
      nome,
      caminho: raiz + partes.slice(0, i + 1).join('/'),
    }));
  });
  destinoFinal(): string {
    const nova = this.novaPasta.trim();
    return nova ? `${this.atual()}/${nova}` : this.atual();
  }

  abrir(): void {
    this.aberto.set(true);
    this.novaPasta = '';
    // Começa onde o campo já aponta (ou no pai, se ainda não existe).
    this.api.pastas(this.valor || '.').subscribe({
      next: () => this.navegar(this.valor || '.'),
      error: () => this.navegar('~'),
    });
  }

  navegar(caminho: string): void {
    this.api.pastas(caminho).subscribe({
      next: (r: PastaResp) => {
        this.atual.set(r.atual);
        this.pai.set(r.pai);
        this.pastas.set(r.pastas);
        this.casa.set(r.casa);
        this.cwd.set(r.servidor_cwd);
        this.erro.set('');
      },
      error: (e) => this.erro.set(e.error?.detail ?? e.message),
    });
  }

  confirmar(): void {
    this.valorChange.emit(this.destinoFinal());
    this.aberto.set(false);
  }

  limparNome(): void {
    this.novaPasta = this.novaPasta.replace(/[/\\]+/g, '');
  }
}
