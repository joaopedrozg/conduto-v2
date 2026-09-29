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
        <p class="grupo">Pipeline</p>
        <a routerLink="/criar" routerLinkActive="ativo" queryParamsHandling="preserve">
          <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 12h4l1.8-4 2.6 8 1.8-4h2.8" /></svg>
          Meu pipeline
        </a>
        <p class="grupo">Administração</p>
        <a routerLink="/admin" routerLinkActive="ativo" queryParamsHandling="preserve">
          <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 12.5a6 6 0 0 1 11 0" /><circle cx="8" cy="12.5" r="1.3" /><path d="M8 12.5l2.6-3.4" /></svg>
          Administrar
        </a>
        <nav class="sub">
          <a routerLink="/admin/visao" routerLinkActive="ativo" queryParamsHandling="preserve">
            <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M1.5 8C3.5 4.8 5.8 3.5 8 3.5s4.5 1.3 6.5 4.5c-2 3.2-4.3 4.5-6.5 4.5S3.5 11.2 1.5 8z" /><circle cx="8" cy="8" r="1.6" /></svg>
            Visão geral
          </a>
          <a routerLink="/admin/ddl" routerLinkActive="ativo" queryParamsHandling="preserve">
            <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="3" width="11" height="10" rx="1.5" /><path d="M2.5 6.3h11M6.3 6.3V13" /></svg>
            DDL
          </a>
          <a routerLink="/admin/schedules" routerLinkActive="ativo" queryParamsHandling="preserve">
            <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="5.5" /><path d="M8 5v3.2l2.2 1.3" /></svg>
            Schedules
          </a>
          <a routerLink="/admin/inferir" routerLinkActive="ativo" queryParamsHandling="preserve">
            <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M8 1.8l1.7 4 4 1.7-4 1.7L8 13.2l-1.7-4-4-1.7 4-1.7z" /></svg>
            Inferir
          </a>
          <a routerLink="/admin/servidores" routerLinkActive="ativo" queryParamsHandling="preserve">
            <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="2.3" width="10" height="4.2" rx="1" /><rect x="3" y="9.5" width="10" height="4.2" rx="1" /></svg>
            Servidores
          </a>
          <a routerLink="/admin/drivers" routerLinkActive="ativo" queryParamsHandling="preserve">
            <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="8" height="8" rx="1.5" /><path d="M6 1.8v2.2M10 1.8v2.2M6 12v2.2M10 12v2.2M1.8 6H4M1.8 10H4M12 6h2.2M12 10h2.2" /></svg>
            Drivers
          </a>
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
    '.lateral { width: 232px; flex-shrink: 0; background: #fff; border-right: 1px solid var(--borda); padding: 14px 12px; display: flex; flex-direction: column; gap: 2px; position: sticky; top: 73px; max-height: calc(100vh - 93px); overflow-y: auto; }',
    '.grupo { margin: 8px 8px 4px; font-size: 0.72em; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--neutro); }',
    '.grupo:first-child { margin-top: 0; }',
    '.lateral a { display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: 8px; text-decoration: none; color: var(--texto); font-weight: 500; }',
    '.lateral a svg { flex-shrink: 0; color: var(--neutro); }',
    '.lateral a:hover { background: var(--fundo); }',
    '.lateral a.ativo { background: #e8f0fe; color: var(--info); font-weight: 700; box-shadow: inset 3px 0 0 var(--info); }',
    '.lateral a.ativo svg { color: var(--info); }',
    '.sub { display: flex; flex-direction: column; gap: 1px; margin: 2px 0 2px 18px; border-left: 2px solid var(--borda); padding-left: 8px; }',
    '.sub a { padding: 7px 10px; font-size: 0.9em; font-weight: 400; }',
    '.sub a.ativo { box-shadow: inset 3px 0 0 var(--info); }',
    '.layout main { flex: 1; min-width: 0; }',
    '@media (max-width: 720px) { .layout { flex-direction: column; } .lateral { width: auto; position: static; max-height: none; flex-direction: row; flex-wrap: wrap; align-items: center; border-right: 0; border-bottom: 1px solid var(--borda); } .grupo { display: none; } .sub { flex-direction: row; flex-wrap: wrap; border-left: 0; margin: 0; padding-left: 0; } }',
  ],
})
export class AppComponent {}
