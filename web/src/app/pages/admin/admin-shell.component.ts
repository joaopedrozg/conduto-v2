import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterOutlet } from '@angular/router';
import { AdminContext } from '../../services/admin-context.service';
import { CriarComponent } from '../criar.component';

/**
 * Casca do Administrar: diretório do projeto + outlet dos submenus
 * (visão geral, ddl, schedules, inferir, servidores, drivers).
 */
@Component({
  selector: 'conduto-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterOutlet],
  template: `
    <div class="timeline">
      <span class="atual">● Administrar {{ ctx.projectDir() }}</span>
    </div>
    <div class="card">
      <label>Diretório do projeto</label>
      <input [ngModel]="ctx.projectDir()" (ngModelChange)="ctx.projectDir.set($event)" />
    </div>
    <router-outlet />
  `,
})
export class AdminShellComponent {
  ctx = inject(AdminContext);
  private rota = inject(ActivatedRoute);

  constructor() {
    // Projeto atual: ?projeto= da URL, senão o contexto guardado pelo wizard.
    const viaUrl = (this.rota.snapshot.queryParamMap.get('projeto') || '').trim();
    const ctx = CriarComponent.lerContexto();
    if (viaUrl) this.ctx.projectDir.set(viaUrl);
    else if (ctx?.dir) this.ctx.projectDir.set(ctx.dir);
  }
}
