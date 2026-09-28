import { Component, EventEmitter, Input, Output, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../services/api.service';

/** Seletor de pasta no servidor (o projeto é criado no backend, não no browser). */
@Component({
  selector: 'conduto-pasta',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="pasta-linha">
      <input [(ngModel)]="valor" placeholder="./meu_projeto" style="flex:1" />
      <button class="secundario" (click)="abrir()">Procurar...</button>
    </div>
    <div class="modal-fundo" *ngIf="aberto()">
      <div class="modal">
        <h3>Escolher pasta no servidor</h3>
        <p class="atual">{{ atual() }}</p>
        <div class="lista">
          <button class="secundario" *ngIf="pai()" (click)="navegar(pai()!)">⬆ .. (voltar)</button>
          <button class="pasta" *ngFor="let p of pastas()" (click)="navegar(atual() + '/' + p)">
            📁 {{ p }}
          </button>
        </div>
        <p class="erro" *ngIf="erro()">{{ erro() }}</p>
        <label>Nova subpasta (opcional)</label>
        <input [(ngModel)]="novaPasta" placeholder="meu_projeto" />
        <div class="acoes">
          <button class="secundario" (click)="aberto.set(false)">Cancelar</button>
          <button (click)="confirmar()">Usar esta pasta</button>
        </div>
      </div>
    </div>
  `,
  styles: [
    '.pasta-linha { display: flex; gap: 8px; }',
    '.modal-fundo { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 10; }',
    '.modal { background: #fff; border-radius: 10px; padding: 20px; width: min(560px, 90vw); max-height: 80vh; overflow: auto; }',
    '.atual { font-family: monospace; font-size: .85em; word-break: break-all; }',
    '.lista { display: flex; flex-direction: column; gap: 4px; max-height: 260px; overflow: auto; margin: 8px 0; }',
    'button.pasta { background: none; border: 0; color: var(--info); text-align: left; padding: 6px; cursor: pointer; margin: 0; }',
    '.erro { color: var(--erro); }',
    '.acoes { display: flex; gap: 8px; justify-content: flex-end; }',
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
  erro = signal('');
  novaPasta = '';

  abrir(): void {
    this.aberto.set(true);
    this.navegar(this.valor || '.');
  }

  navegar(caminho: string): void {
    this.api.pastas(caminho).subscribe({
      next: (r) => {
        this.atual.set(r.atual);
        this.pai.set(r.pai);
        this.pastas.set(r.pastas);
        this.erro.set('');
      },
      error: (e) => this.erro.set(e.error?.detail ?? e.message),
    });
  }

  confirmar(): void {
    let destino = this.atual();
    const nova = this.novaPasta.trim().replace(/[/\\]+/g, '');
    if (nova) destino += '/' + nova;
    this.valorChange.emit(destino);
    this.aberto.set(false);
  }
}
