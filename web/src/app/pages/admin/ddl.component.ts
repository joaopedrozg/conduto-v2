import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ToastService } from '../../services/toast.service';
import { AdminContext } from '../../services/admin-context.service';
import { notificarErro } from '../../services/erro-api';

@Component({
  selector: 'conduto-admin-ddl',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2>DDL</h2>
      <button (click)="verDdl(false)">Gerar DDL</button>
      <button class="secundario" (click)="verDdl(true)">Aplicar no destino</button>
    </div>
    <pre class="log" *ngIf="log()">{{ log() }}</pre>
    <pre class="log" *ngIf="ddl()">{{ ddl() }}</pre>
  `,
})
export class DdlComponent {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  private ctx = inject(AdminContext);
  log = signal('');
  ddl = signal('');

  verDdl(aplicar: boolean): void {
    this.api.ddl(this.ctx.projectDir(), aplicar).subscribe({
      next: (r) => {
        this.ddl.set(r.ddl);
        this.toast.ok(`${r.comandos} comando(s), ${r.aplicados} aplicado(s).`);
      },
      error: (e) => notificarErro(this.toast, e, 'DDL'),
    });
  }
}
