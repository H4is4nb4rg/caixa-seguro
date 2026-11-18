import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, mensagemDeErro } from '../servicos/api.service';

@Component({
  selector: 'app-login',
  imports: [FormsModule],
  template: `
  <div class="tela">
    <header class="topbar"><div><div class="titulo">Caixa Seguro</div><div class="usuario">Maria Bunita Moda</div></div></header>
    <form class="conteudo" (ngSubmit)="entrar()">
      <div>
        <label class="rotulo" for="login">Login</label>
        <input id="login" name="login" class="campo" autocomplete="username" [(ngModel)]="login" required maxlength="50">
      </div>
      <div>
        <label class="rotulo" for="senha">Senha</label>
        <input id="senha" name="senha" class="campo" [type]="mostrar() ? 'text' : 'password'" autocomplete="current-password" [(ngModel)]="senha" required maxlength="128">
        <button type="button" class="btn-peq" style="margin-top:8px" (click)="mostrar.set(!mostrar())" [attr.aria-pressed]="mostrar()">
          {{ mostrar() ? 'Ocultar senha' : 'Mostrar senha' }}
        </button>
      </div>
      @if (erro()) { <p class="msg-erro" role="alert">⚠ {{ erro() }}</p> }
      <button class="btn primario" type="submit" [disabled]="enviando()">Entrar</button>
    </form>
  </div>`,
})
export class LoginPagina {
  private api = inject(ApiService);
  private router = inject(Router);
  login = '';
  senha = '';
  mostrar = signal(false);
  erro = signal('');
  enviando = signal(false);

  entrar() {
    if (!this.login || !this.senha) { this.erro.set('Informe login e senha.'); return; }
    this.enviando.set(true);
    this.api.login(this.login.trim(), this.senha).subscribe({
      next: (r) => { this.api.iniciarSessao(r.access_token, r.usuario); this.router.navigateByUrl('/inicio'); },
      error: (e) => { this.erro.set(mensagemDeErro(e)); this.enviando.set(false); },
    });
  }
}
