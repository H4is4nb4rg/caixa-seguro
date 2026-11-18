import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, Caixa, NOMES_PERFIL, mensagemDeErro, normalizarValor, reais } from '../servicos/api.service';

/** Tela 3a — confirmação da movimentação registrada. */
@Component({
  selector: 'app-confirmacao',
  imports: [DatePipe],
  template: `
  <div class="tela">
    <header class="topbar"><div style="flex:1"><div class="titulo">Movimentação registrada</div>
      <div class="usuario">{{ api.usuario()?.nome }}</div></div></header>
    <main class="conteudo">
      @if (api.ultimoRegistro(); as r) {
        <div class="estado ok" role="status"><span class="icone" aria-hidden="true">✔</span>
          <div>{{ r.movimentacao.tipo === 'venda' ? 'Venda registrada' : 'Movimentação registrada' }}
            <span class="sub">{{ reais(r.movimentacao.valor) }}@if (r.movimentacao.forma_pagamento) { via {{ r.movimentacao.forma_pagamento.toUpperCase() }} }
              às {{ r.movimentacao.registrado_em | date:'HH:mm' }}, por {{ r.movimentacao.responsavel }}</span></div></div>
        <div class="card"><div class="linha"><span>Dinheiro esperado no caixa</span><b>{{ reais(r.saldo_esperado) }}</b></div></div>
      }
      <button class="btn primario" (click)="router.navigateByUrl('/movimentacao')">＋ Nova movimentação</button>
      <button class="btn secundario" (click)="router.navigateByUrl('/inicio')">Voltar ao início</button>
    </main>
  </div>`,
})
export class ConfirmacaoPagina {
  api = inject(ApiService);
  router = inject(Router);
  reais = reais;
}

/** Tela 3b — fechamento do caixa com conferência e alerta de diferença. */
@Component({
  selector: 'app-fechamento',
  imports: [FormsModule, DatePipe],
  template: `
  <div class="tela">
    <header class="topbar">
      <button class="btn-ghost" (click)="router.navigateByUrl('/inicio')">‹ Início</button>
      <div style="flex:1"><div class="titulo">Fechamento do caixa</div><div class="usuario">{{ api.usuario()?.nome }} · Perfil {{ perfil() }}</div></div>
    </header>
    <main class="conteudo">
      @if (fechado(); as c) {
        <div class="estado neutro" role="status"><span class="icone" aria-hidden="true">🔒</span>
          <div>Caixa fechado<span class="sub">às {{ c.fechado_em | date:'HH:mm' }} · diferença {{ reais(c.divergencia) }}</span></div></div>
        <button class="btn primario" (click)="router.navigateByUrl('/inicio')">Voltar ao início</button>
      } @else {
        <div class="card">
          <h2>Conferência do dinheiro em caixa</h2>
          <div class="linha"><span>Valor inicial</span><b>{{ reais(valorInicial()) }}</b></div>
          <div class="linha"><span>Valor esperado</span><span class="grande">{{ reais(esperado()) }}</span></div>
          <p class="muted">Calculado automaticamente pelo sistema.</p>
        </div>
        <div>
          <label class="rotulo" for="contado">Valor contado (R$)</label>
          <input id="contado" class="campo" inputmode="decimal" placeholder="Ex.: 602,40" [(ngModel)]="contado" (ngModelChange)="erro.set('')">
        </div>
        @if (diferenca() !== null && diferenca() !== 0) {
          <div class="estado alerta" role="alert"><span class="icone" aria-hidden="true">⚠</span>
            <div>Diferença: {{ reais(abs(diferenca()!)) }} {{ diferenca()! < 0 ? 'faltando' : 'sobrando' }}
              <span class="sub">{{ diferenca()! < 0 ? 'Contado é menor que o esperado.' : 'Contado é maior que o esperado.' }}</span></div></div>
        } @else if (diferenca() === 0) {
          <div class="estado ok" role="status"><span class="icone" aria-hidden="true">✔</span><div>Caixa confere<span class="sub">Sem diferença.</span></div></div>
        }
        <div>
          <label class="rotulo" for="just">Justificativa (obrigatória quando há diferença)</label>
          <textarea id="just" class="campo" [class.erro]="erro()" maxlength="300" [(ngModel)]="justificativa"></textarea>
          @if (erro()) { <p class="msg-erro" role="alert">⚠ {{ erro() }}</p> }
        </div>
      }
    </main>
    @if (!fechado()) {
      <div class="rodape"><button class="btn primario" [disabled]="enviando()" (click)="fechar()">🔒 Confirmar fechamento</button></div>
    }
  </div>`,
})
export class FechamentoPagina implements OnInit {
  api = inject(ApiService);
  router = inject(Router);
  reais = reais;
  abs = Math.abs;
  esperado = signal<string | null>(null);
  valorInicial = signal<string | null>(null);
  contado = '';
  justificativa = '';
  erro = signal('');
  enviando = signal(false);
  fechado = signal<Caixa | null>(null);
  perfil = computed(() => { const u = this.api.usuario(); return u ? NOMES_PERFIL[u.perfil] : ''; });

  ngOnInit() {
    this.api.resumo().subscribe({
      next: (r) => { this.esperado.set(r.saldo_esperado); this.valorInicial.set(r.caixa?.valor_inicial ?? null); },
      error: (e) => this.erro.set(mensagemDeErro(e)),
    });
  }

  diferenca(): number | null {
    const v = normalizarValor(this.contado);
    if (v === null || this.esperado() === null) return null;
    return Math.round((Number(v) - Number(this.esperado())) * 100) / 100;
  }

  fechar() {
    const v = normalizarValor(this.contado);
    if (v === null) { this.erro.set('Informe o valor contado. Ex.: 602,40'); return; }
    if (this.diferenca() !== 0 && !this.justificativa.trim()) { this.erro.set('Explique a diferença para fechar o caixa.'); return; }
    this.enviando.set(true);
    this.api.fechar(v, this.justificativa.trim() || null).subscribe({
      next: (c) => this.fechado.set(c),
      error: (e) => { this.erro.set(mensagemDeErro(e)); this.enviando.set(false); },
    });
  }
}
