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
      <span class="logo" aria-hidden="true">
        <svg viewBox="0 0 32 32" width="32" height="32">
          <defs>
            <linearGradient id="conduto-g" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#2f81f7" />
              <stop offset="1" stop-color="#0d419d" />
            </linearGradient>
          </defs>
          <rect x="1" y="1" width="30" height="30" rx="9" fill="url(#conduto-g)" />
          <path
            d="M7 16h5l2.5-6 4 12 2.5-6H25"
            fill="none" stroke="#fff" stroke-width="2.4"
            stroke-linecap="round" stroke-linejoin="round"
          />
        </svg>
      </span>
      <span class="titulos">
        <strong>conduto</strong>
        <small>o duto que leva seus dados da origem ao destino</small>
      </span>
      <span class="meta">Web UI <i>·</i> TUI em <code>conduto init</code></span>
    </header>
    <div class="layout">
      <aside class="lateral">
        <a routerLink="/criar" routerLinkActive="ativo" queryParamsHandling="preserve">Meu pipeline</a>
        <a routerLink="/admin" routerLinkActive="ativo" queryParamsHandling="preserve">Administrar</a>
        <nav class="sub">
          <a routerLink="/admin/visao" routerLinkActive="ativo" queryParamsHandling="preserve">Visão geral</a>
          <a routerLink="/admin/ddl" routerLinkActive="ativo" queryParamsHandling="preserve">DDL</a>
          <a routerLink="/admin/schedules" routerLinkActive="ativo" queryParamsHandling="preserve">Schedules</a>
          <a routerLink="/admin/inferir" routerLinkActive="ativo" queryParamsHandling="preserve">Inferir</a>
          <a routerLink="/admin/servidores" routerLinkActive="ativo" queryParamsHandling="preserve">Servidores</a>
          <a routerLink="/admin/drivers" routerLinkActive="ativo" queryParamsHandling="preserve">Drivers</a>
        </nav>
      </aside>
      <main><router-outlet /></main>
    </div>
  `,
  styles: [
    'header.marca { position: sticky; top: 0; z-index: 50; display: flex; align-items: center; gap: 12px; padding: 10px 20px; background: linear-gradient(100deg, #0d1117 30%, #13233f 100%); color: #fff; border-bottom: 1px solid #30363d; }',
    '.logo { display: inline-flex; filter: drop-shadow(0 1px 3px rgba(0,0,0,.5)); }',
    '.titulos { display: flex; flex-direction: column; line-height: 1.25; }',
    '.titulos strong { font-size: 1.15em; letter-spacing: 0.02em; }',
    '.titulos small { color: #9da7b3; font-size: 0.82em; }',
    '.meta { margin-left: auto; color: #9da7b3; font-size: 0.85em; white-space: nowrap; }',
    '.meta i { font-style: normal; opacity: .6; margin: 0 4px; }',
    '.meta code { background: rgba(255,255,255,.12); border: 0; color: #e6edf3; }',
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
