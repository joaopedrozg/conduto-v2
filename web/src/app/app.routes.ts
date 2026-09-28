import { Routes } from '@angular/router';
import { CriarComponent } from './pages/criar.component';
import { AdminComponent } from './pages/admin.component';

export const routes: Routes = [
  { path: '', redirectTo: 'criar', pathMatch: 'full' },
  { path: 'criar', component: CriarComponent },
  { path: 'admin', component: AdminComponent },
];
