import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, CRON_PRESETS } from '../../services/api.service';
import { ToastService } from '../../services/toast.service';
import { AdminContext } from '../../services/admin-context.service';
import { notificarErro } from '../../services/erro-api';

@Component({
  selector: 'conduto-admin-schedules',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="card">
      <h2>Schedules</h2>
      <label>Frequência (vazio = mantém)</label>
      <select [(ngModel)]="cronPreset">
        <option value="">Manter atual</option>
        <option *ngFor="let f of presets" [value]="f.id">{{ f.rotulo }}</option>
      </select>
      <input *ngIf="cronPreset === 'custom'" [(ngModel)]="cronCustom" placeholder="Ex.: 30 8 * * 1-5" />
      <div>
        <button (click)="regenerar()">Regenerar schedules</button>
      </div>
    </div>
    <pre class="log" *ngIf="log()">{{ log() }}</pre>
  `,
})
export class SchedulesComponent {
  private api = inject(ApiService);
  private toast = inject(ToastService);
  private ctx = inject(AdminContext);
  presets = CRON_PRESETS;
  cronPreset = '';
  cronCustom = '';
  log = signal('');

  regenerar(): void {
    const cron = this.cronPreset === 'custom' ? this.cronCustom.trim() : this.presetCron(this.cronPreset);
    this.api.schedules(this.ctx.projectDir(), cron || undefined).subscribe({
      next: (r) => {
        this.log.set(JSON.stringify(r, null, 2));
        this.toast.ok('Schedules regenerados.');
      },
      error: (e) => notificarErro(this.toast, e, 'Schedules'),
    });
  }

  private presetCron(id: string): string {
    return this.presets.find((p) => p.id === id)?.cron ?? '';
  }
}
