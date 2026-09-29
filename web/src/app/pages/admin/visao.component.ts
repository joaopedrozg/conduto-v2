import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ToastService } from '../../services/toast.service';
import { AdminContext } from '../../services/admin-context.service';
import { notificarErro } from '../../services/erro-api';

@Component({
  selector: 'conduto-admin-visao',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2>Visão geral</h2>
      <button (click)="resumo()">Atualizar</button>
    </div>
    <pre class="log" *ngIf="log()">{{ log() }}</pre>
  `,
})
export class VisaoComponent {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  private ctx = inject(AdminContext);
  log = signal('');

  constructor() {
    if (this.ctx.projectDir() !== '.') this.resumo();
  }

  resumo(): void {
    this.api.resumo(this.ctx.projectDir()).subscribe({
      next: (r) => this.log.set(JSON.stringify(r, null, 2)),
      error: (e) => notificarErro(this.toast, e, 'Visão geral'),
    });
  }
}
