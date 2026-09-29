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
        <a routerLink="/criar" routerLinkActive="ativo">Criar projeto</a>
        <a routerLink="/admin" routerLinkActive="ativo">Administrar</a>
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
    '.layout main { flex: 1; min-width: 0; }',
    '@media (max-width: 720px) { .layout { flex-direction: column; } .lateral { width: auto; flex-direction: row; border-right: 0; border-bottom: 1px solid var(--borda); } }',
  ],
})
export class AppComponent {}
