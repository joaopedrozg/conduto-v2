import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { ToastsComponent } from './components/toasts.component';

@Component({
  selector: 'conduto-root',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, RouterOutlet, ToastsComponent],
  template: `
    <conduto-toasts />
    <header class="marca">
      <strong>conduto web</strong> — o duto que leva seus dados da origem ao destino
      <span style="opacity:.7"> · TUI mantida em <code>conduto init</code></span>
    </header>
    <div class="layout">
      <aside class="lateral">
        <a routerLink="/criar" routerLinkActive="ativo">Meu pipeline</a>
        <a routerLink="/admin" routerLinkActive="ativo">Administrar</a>
        <nav class="sub">
          <a routerLink="/admin/visao" routerLinkActive="ativo">Visão geral</a>
          <a routerLink="/admin/ddl" routerLinkActive="ativo">DDL</a>
          <a routerLink="/admin/schedules" routerLinkActive="ativo">Schedules</a>
          <a routerLink="/admin/inferir" routerLinkActive="ativo">Inferir</a>
          <a routerLink="/admin/servidores" routerLinkActive="ativo">Servidores</a>
          <a routerLink="/admin/drivers" routerLinkActive="ativo">Drivers</a>
        </nav>
      </aside>
      <main><router-outlet /></main>
    </div>
  `,
  styles: [
    '.layout { display: flex; align-items: stretch; }',
    '.lateral { width: 220px; flex-shrink: 0; background: #fff; border-right: 1px solid var(--borda); padding: 12px; display: flex; flex-direction: column; gap: 4px; }',
    '.lateral a { padding: 10px 12px; border-radius: 6px; text-decoration: none; color: var(--neutro); }',
    '.lateral a:hover { background: var(--fundo); }',
    '.lateral a.ativo { background: #e8f0fe; color: var(--info); font-weight: bold; }',
    '.sub { display: flex; flex-direction: column; gap: 2px; margin: 2px 0 2px 12px; border-left: 2px solid var(--borda); padding-left: 6px; }',
    '.sub a { padding: 7px 10px; font-size: .92em; }',
    '.layout main { flex: 1; min-width: 0; }',
    '@media (max-width: 720px) { .layout { flex-direction: column; } .lateral { width: auto; flex-direction: row; border-right: 0; border-bottom: 1px solid var(--borda); } }',
  ],
})
export class AppComponent {}
