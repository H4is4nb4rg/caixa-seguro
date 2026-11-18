import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, NOMES_PERFIL, Resumo, mensagemDeErro, normalizarValor, reais } from '../servicos/api.service';

@Component({
  selector: 'app-inicio',
  imports: [FormsModule, DatePipe],
  template: `
  <div class="tela">
    <header class="topbar">
      <div style="flex:1"><div class="titulo">Caixa Seguro</div><div class="usuario">{{ api.usuario()?.nome }} · Perfil {{ perfil() }}</div></div>
      <button class="btn-ghost" (click)="sair()">⎋ Sair</button>
    </header>
    <main class="conteudo">
      @if (resumo(); as r) {
        @if (aberto()) {
          <div class="estado ok" role="status"><span class="icone" aria-hidden="true">🔓</span>
            <div>Caixa aberto<span class="sub">desde {{ r.caixa!.aberto_em | date:'HH:mm' }}</span></div></div>
          <div class="card">
            <h2>Resumo de hoje</h2>
            <div class="linha"><span>Valor inicial</span><b>{{ reais(r.caixa!.valor_inicial) }}</b></div>
            <div class="linha"><span>Movimentações</span><b>{{ r.quantidade_movimentacoes }}</b></div>
          </div>
          <button class="btn primario" (click)="router.navigateByUrl('/movimentacao')">＋ Nova movimentação</button>
          @if (podeAbrirFechar()) {
            <button class="btn secundario" (click)="router.navigateByUrl('/fechamento')">🔒 Fechar caixa</button>
          }
        } @else {
          <div class="estado neutro" role="status"><span class="icone" aria-hidden="true">🔒</span>
            <div>Caixa fechado<span class="sub">Abra o caixa para registrar movimentações.</span></div></div>
          @if (podeAbrirFechar()) {
            <div>
              <label class="rotulo" for="inicial">Valor inicial em dinheiro (R$)</label>
              <input id="inicial" class="campo" [class.erro]="erro()" inputmode="decimal" placeholder="Ex.: 150,00" [(ngModel)]="valorInicial">
              @if (erro()) { <p class="msg-erro" role="alert">⚠ {{ erro() }}</p> }
            </div>
            <button class="btn primario" (click)="abrir()">🔓 Abrir caixa</button>
          } @else {
            <p class="muted">Peça a abertura do caixa para a responsável.</p>
          }
        }
        @if (ehProprietaria()) {
          <button class="btn secundario" (click)="router.navigateByUrl('/painel')">📊 Painel da loja</button>
        }
      } @else {
        <p class="muted" role="status">{{ erro() || 'Carregando...' }}</p>
      }
    </main>
  </div>`,
})
export class InicioPagina implements OnInit {
  api = inject(ApiService);
  router = inject(Router);
  reais = reais;
  resumo = signal<Resumo | null>(null);
  erro = signal('');
  valorInicial = '';
  perfil = computed(() => { const u = this.api.usuario(); return u ? NOMES_PERFIL[u.perfil] : ''; });
  podeAbrirFechar = computed(() => ['proprietaria', 'caixa'].includes(this.api.usuario()?.perfil ?? ''));
  ehProprietaria = computed(() => this.api.usuario()?.perfil === 'proprietaria');
  aberto = computed(() => this.resumo()?.caixa?.status === 'aberto');

  ngOnInit() { this.carregar(); }

  carregar() {
    this.api.resumo().subscribe({ next: (r) => this.resumo.set(r), error: (e) => this.erro.set(mensagemDeErro(e)) });
  }

  abrir() {
    const valor = normalizarValor(this.valorInicial);
    if (valor === null) { this.erro.set('Informe o valor inicial. Ex.: 150,00'); return; }
    this.erro.set('');
    this.api.abrir(valor).subscribe({ next: () => this.carregar(), error: (e) => this.erro.set(mensagemDeErro(e)) });
  }

  sair() {
    this.api.logout().subscribe({ complete: () => this.finalizar(), error: () => this.finalizar() });
  }

  private finalizar() { this.api.encerrarSessao(); this.router.navigateByUrl('/login'); }
}
