import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterOutlet } from '@angular/router';
import { AdminContext } from '../../services/admin-context.service';

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
    // Projeto atual via URL (?projeto= ou ?dir=, preservados na sidebar).
    const params = this.rota.snapshot.queryParamMap;
    const dir = (params.get('projeto') || params.get('dir') || '').trim();
    if (dir) this.ctx.projectDir.set(dir);
  }
}
