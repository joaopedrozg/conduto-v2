import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ToastService } from '../../services/toast.service';
import { AdminContext } from '../../services/admin-context.service';
import { notificarErro } from '../../services/erro-api';

@Component({
  selector: 'conduto-admin-inferir',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2>Inferir colunas</h2>
      <label>Tabela (vazio = todas sem colunas)</label>
      <input [(ngModel)]="tabela" placeholder="Ex.: clientes" />
      <div>
        <button (click)="inferir()">Inferir da origem</button>
      </div>
    </div>
    <pre class="log" *ngIf="log()">{{ log() }}</pre>
  `,
})
export class InferirComponent {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  private ctx = inject(AdminContext);
  tabela = '';
  log = signal('');

  inferir(): void {
    this.api.inferir(this.ctx.projectDir(), this.tabela.trim() || undefined).subscribe({
      next: (r) => {
        this.log.set(JSON.stringify(r, null, 2));
        this.toast.ok('Colunas inferidas.');
      },
      error: (e) => notificarErro(this.toast, e, 'Inferir'),
    });
  }
}
