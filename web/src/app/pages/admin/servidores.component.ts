import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ToastService } from '../../services/toast.service';
import { AdminContext } from '../../services/admin-context.service';
import { notificarErro } from '../../services/erro-api';

@Component({
  selector: 'conduto-admin-servidores',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2>Servidor Dagster</h2>
      <p *ngIf="dagster().responde">No ar em <a [href]="dagster().url" target="_blank">{{ dagster().url }}</a><span *ngIf="dagster().externo"> (externo — subido fora da Web UI)</span></p>
      <p *ngIf="dagster().rodando && !dagster().responde">Iniciando...</p>
      <p *ngIf="!dagster().rodando && !dagster().responde">Parado.</p>
      <button (click)="iniciar()" [disabled]="dagster().rodando || dagster().responde">Subir servidor</button>
      <button class="secundario" (click)="atualizar()">Atualizar status</button>
      <button class="secundario" (click)="parar()" [disabled]="!dagster().rodando">Parar</button>
      <p class="contagem" *ngIf="dagster().externo">Servidor externo: pare pelo terminal que o subiu.</p>
    </div>
  `,
  styles: ['.contagem { color: var(--neutro); font-size: .9em; }'],
})
export class ServidoresComponent {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  private ctx = inject(AdminContext);
  dagster = signal<{ rodando: boolean; responde: boolean; externo: boolean; pid: number | null; url: string }>(
    { rodando: false, responde: false, externo: false, pid: null, url: 'http://localhost:3000' },
  );

  constructor() {
    if (this.ctx.projectDir() !== '.') this.atualizar();
  }

  atualizar(): void {
    this.api.dagsterStatus(this.ctx.projectDir()).subscribe({
      next: (r) => this.dagster.set(r),
      error: (e) => notificarErro(this.toast, e, 'Dagster'),
    });
  }

  iniciar(): void {
    this.toast.info('Subindo o servidor Dagster...');
    this.api.dagsterIniciar(this.ctx.projectDir()).subscribe({
      next: (r) => {
        this.dagster.set({ ...r, responde: false, externo: false });
        this.toast.info(`Dagster subindo (PID ${r.pid}). Aguarde e clique em Atualizar status.`);
      },
      error: (e) => notificarErro(this.toast, e, 'Dagster'),
    });
  }

  parar(): void {
    this.api.dagsterParar(this.ctx.projectDir()).subscribe({
      next: (r) => {
        this.dagster.set({ rodando: r.rodando, responde: false, externo: false, pid: null, url: 'http://localhost:3000' });
        this.toast.ok('Servidor Dagster parado.');
      },
      error: (e) => notificarErro(this.toast, e, 'Dagster'),
    });
  }
}
