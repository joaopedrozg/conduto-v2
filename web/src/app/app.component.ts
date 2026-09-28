import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'conduto-root',
  standalone: true,
  imports: [RouterLink, RouterOutlet],
  template: `
    <header class="marca">
      <strong>conduto web</strong> — o duto que leva seus dados da origem ao destino
      <span style="opacity:.7"> · TUI mantida em <code>conduto init</code></span>
    </header>
    <nav class="menu">
      <a routerLink="/criar">Criar projeto</a>
      <a routerLink="/admin">Administrar</a>
      <a href="/docs" target="_blank">API</a>
    </nav>
    <main><router-outlet /></main>
  `,
})
export class AppComponent {}
