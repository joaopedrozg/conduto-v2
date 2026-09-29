import { Injectable, signal } from '@angular/core';

/** Diretório do projeto administrado, compartilhado pelos submenus. */
@Injectable({ providedIn: 'root' })
export class AdminContext {
  projectDir = signal('.');
}
