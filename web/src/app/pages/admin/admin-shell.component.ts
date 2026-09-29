import { Component, inject } from '@angular/core';
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
  imports: [RouterOutlet],
  template: `
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
