import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService } from '../services/toast.service';

@Component({
  selector: 'conduto-toasts',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toasts" aria-live="polite">
      <div *ngFor="let t of toast.toasts()" [class]="'toast ' + t.tipo">
        <span class="texto">{{ t.texto }}</span>
        <button class="fechar" (click)="toast.fechar(t.id)" aria-label="Fechar">×</button>
      </div>
    </div>
  `,
  styles: [
    '.toasts { position: fixed; top: 12px; right: 12px; z-index: 100; display: flex; flex-direction: column; gap: 8px; width: min(400px, 90vw); }',
    '.toast { display: flex; gap: 8px; align-items: flex-start; background: #fff; border: 1px solid var(--borda); border-left: 4px solid var(--info); border-radius: 8px; padding: 10px 12px; box-shadow: 0 4px 16px rgba(0,0,0,.15); }',
    '.toast.ok { border-left-color: var(--ok); }',
    '.toast.erro { border-left-color: var(--erro); }',
    '.texto { flex: 1; font-size: .9em; white-space: pre-wrap; word-break: break-word; max-height: 200px; overflow: auto; margin: 0; }',
    '.fechar { background: none; border: 0; color: var(--neutro); cursor: pointer; padding: 0 2px; margin: 0; font-size: 1.1em; }',
  ],
})
export class ToastsComponent {
  toast = inject(ToastService);
}
