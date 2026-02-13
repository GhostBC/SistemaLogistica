/**
 * Sistema de Logística - Interface
 * Consome a API em /api/*
 */

const API_BASE = '';

let token = localStorage.getItem('token');
let usuario = JSON.parse(localStorage.getItem('usuario') || 'null');
/** Loja selecionada no submenu Pedidos: null = Todos, ou nome da loja (ex: TikTok) */
let pedidosLojaAtual = null;
/** Filtro de loja selecionado na coluna Loja: null = Todas, ou nome da loja */
let filtroLojaSelecionado = null;
/** Filtro de loja na aba Finalizados */
let filtroLojaFinalizados = null;
let orderByFinalizados = 'data_finalizacao';
let sortDirFinalizados = 'desc';
/** Paginação: página atual (1-based) para Pedidos e Finalizados */
let pagePedidos = 1;
let pageFinalizados = 1;
const PER_PAGE = 100;
/** Lista de todas as lojas disponíveis */
const LOJAS_DISPONIVEIS = [
  'TikTok',
  'Shopee',
  'Tray',
  'Mercado Livre',
  'Shein',
  'Época',
  'BLZWEB',
  'Loja Física',
  'Ifood',
  'Amazon Serviços de Varejo do Brasil Ltda'
];

// Inicialização
document.addEventListener('DOMContentLoaded', function () {
  if (token && usuario) {
    mostrarApp();
    document.querySelector('.menu button[data-pagina="dashboard"]').click();
  } else {
    document.getElementById('tela-login').classList.remove('oculto');
    document.getElementById('app').classList.add('oculto');
  }

  document.querySelectorAll('.menu button[data-pagina]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var pagina = this.getAttribute('data-pagina');
      irPara(pagina);
    });
  });
  
  // Event listeners para busca em tempo real
  var buscaInputPedidos = document.getElementById('busca-pedidos');
  if (buscaInputPedidos) {
    buscaInputPedidos.addEventListener('input', function() {
      // Debounce: aguardar 500ms após parar de digitar
      clearTimeout(timeoutBuscaPedidos);
      timeoutBuscaPedidos = setTimeout(function() {
        carregarPedidos();
      }, 500);
    });
  }
  
  // Event listeners para edição de meta diária
  const btnEditarMeta = document.getElementById('dashboard-btn-editar-meta');
  const btnSalvarMeta = document.getElementById('dashboard-btn-salvar-meta');
  const btnCancelarMeta = document.getElementById('dashboard-btn-cancelar-meta');
  const metaInput = document.getElementById('dashboard-ideal-media-input');
  const metaDisplay = document.getElementById('dashboard-ideal-media-display');
  
  if (btnEditarMeta && btnSalvarMeta && btnCancelarMeta && metaInput && metaDisplay) {
    let valorOriginalMeta = null;
    
    btnEditarMeta.addEventListener('click', function() {
      valorOriginalMeta = metaInput.value;
      metaInput.style.display = 'inline-block';
      metaDisplay.style.display = 'none';
      btnEditarMeta.style.display = 'none';
      btnSalvarMeta.style.display = 'inline-block';
      btnCancelarMeta.style.display = 'inline-block';
      metaInput.focus();
    });
    
    btnSalvarMeta.addEventListener('click', function() {
      const novaMeta = parseInt(metaInput.value);
      if (isNaN(novaMeta) || novaMeta < 1) {
        alert('A meta deve ser um número inteiro positivo');
        return;
      }
      
      // Salvar no backend
      api('/api/dashboard/meta', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ meta_diaria: novaMeta })
      })
      .then(function(r) {
        if (!r.ok) {
          return r.json().then(function(err) {
            throw new Error(err.erro || 'Erro ao salvar meta');
          });
        }
        return r.json();
      })
      .then(function(data) {
        metaDisplay.textContent = novaMeta;
        metaInput.style.display = 'none';
        metaDisplay.style.display = 'inline';
        btnEditarMeta.style.display = 'inline-block';
        btnSalvarMeta.style.display = 'none';
        btnCancelarMeta.style.display = 'none';
        valorOriginalMeta = null;
        
        // Recarregar dashboard para atualizar percentual
        carregarDashboard();
      })
      .catch(function(err) {
        alert(err.message || 'Erro ao salvar meta');
      });
    });
    
    btnCancelarMeta.addEventListener('click', function() {
      if (valorOriginalMeta !== null) {
        metaInput.value = valorOriginalMeta;
      }
      metaInput.style.display = 'none';
      metaDisplay.style.display = 'inline';
      btnEditarMeta.style.display = 'inline-block';
      btnSalvarMeta.style.display = 'none';
      btnCancelarMeta.style.display = 'none';
      valorOriginalMeta = null;
    });
  }
  
  var buscaInputFinalizados = document.getElementById('busca-finalizados');
  if (buscaInputFinalizados) {
    buscaInputFinalizados.addEventListener('input', function() {
      clearTimeout(timeoutBuscaFinalizados);
      timeoutBuscaFinalizados = setTimeout(function() {
        carregarFinalizados();
      }, 500);
    });
  }

  var planilhaMandaeInput = document.getElementById('planilha-mandae-input');
  if (planilhaMandaeInput) {
    planilhaMandaeInput.addEventListener('change', function() {
      var file = this.files && this.files[0];
      this.value = '';
      if (!file) return;
      var avisoEl = document.getElementById('planilha-mandae-aviso');
      avisoEl.textContent = 'Enviando planilha...';
      avisoEl.classList.remove('oculto');
      avisoEl.style.color = '#0066cc';
      var formData = new FormData();
      formData.append('planilha', file);
      var h = {};
      if (token) h['Authorization'] = 'Bearer ' + token;
      fetch(API_BASE + '/api/pedidos/planilha-mandae', {
        method: 'POST',
        headers: h,
        body: formData
      })
        .then(function(r) {
          return r.json().then(function(d) {
            if (!r.ok) throw new Error(d.erro || 'Erro ao processar planilha');
            return d;
          });
        })
        .then(function(d) {
          avisoEl.textContent = d.mensagem || (d.atualizados + ' pedido(s) atualizado(s).');
          avisoEl.style.color = '#006600';
          carregarFinalizados();
        })
        .catch(function(e) {
          avisoEl.textContent = e.message || 'Erro ao enviar planilha.';
          avisoEl.style.color = '#cc0000';
        });
    });
  }
});

function headers() {
  const h = { 'Content-Type': 'application/json' };
  if (token) h['Authorization'] = 'Bearer ' + token;
  return h;
}

function api(url, options, attempt) {
  attempt = attempt || 1;
  return fetch(API_BASE + url, {
    ...(options || {}),
    headers: { ...headers(), ...((options && options.headers) || {}) },
  })
    .then(function (r) {
      if (r.status === 401 || r.status === 422) {
        sair();
        throw new Error(r.status === 422 ? 'Sessão inválida. Faça login novamente.' : 'Sessão expirada');
      }
      if (r.status === 429 && attempt < 3) {
        return new Promise(function (resolve) { setTimeout(resolve, 5000); }).then(function () {
          return api(url, options, attempt + 1);
        });
      }
      return r;
    })
    .catch(function (err) {
      if (attempt >= 3) throw err;
      return new Promise(function (resolve) { setTimeout(resolve, 5000); }).then(function () {
        return api(url, options, attempt + 1);
      });
    });
}

function fazerLogin(e) {
  e.preventDefault();
  const email = document.getElementById('login-email').value.trim();
  const senha = document.getElementById('login-senha').value;
  const erroEl = document.getElementById('login-erro');
  erroEl.textContent = '';

  fetch(API_BASE + '/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, senha }),
  })
    .then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.erro || 'Erro ao entrar');
        return data;
      });
    })
    .then(function (data) {
      if (!data.access_token || !data.user) {
        erroEl.textContent = 'Resposta inválida do servidor (token ou usuário ausente).';
        return;
      }
      token = data.access_token;
      usuario = data.user;
      localStorage.setItem('token', token);
      localStorage.setItem('usuario', JSON.stringify(usuario));
      mostrarApp();
      irPara('dashboard');
    })
    .catch(function (err) {
      erroEl.textContent = err.message || 'Erro ao fazer login';
    });

  return false;
}

function sair() {
  token = null;
  usuario = null;
  localStorage.removeItem('token');
  localStorage.removeItem('usuario');
  document.getElementById('app').classList.add('oculto');
  document.getElementById('tela-login').classList.remove('oculto');
  document.getElementById('login-erro').textContent = '';
}

function mostrarApp() {
  document.getElementById('tela-login').classList.add('oculto');
  document.getElementById('app').classList.remove('oculto');
  document.getElementById('user-nome').textContent = usuario ? usuario.nome || usuario.email : '';
}

function irPara(pagina) {
  document.querySelectorAll('.pagina').forEach(function (p) {
    p.classList.add('oculto');
  });
  document.querySelectorAll('.menu button[data-pagina]').forEach(function (b) {
    b.classList.remove('ativo');
    if (b.getAttribute('data-pagina') === pagina) b.classList.add('ativo');
  });

  var el = document.getElementById('pagina-' + pagina);
  if (el) el.classList.remove('oculto');

  if (pagina === 'dashboard') carregarDashboard();
  if (pagina === 'pedidos') {
    atualizarTituloPedidos();
    carregarPedidos();
  }
  if (pagina === 'embalagens') carregarEmbalagens();
  if (pagina === 'finalizados') carregarFinalizados();
  if (pagina === 'relatorios') {
    var dataEl = document.getElementById('relatorio-data');
    if (!dataEl.value) dataEl.value = new Date().toISOString().slice(0, 10);
  }
  if (pagina === 'bling') carregarBlingStatus();
}

function carregarMenuLojas() {
  api('/api/pedidos/lojas')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var sub = document.getElementById('menu-pedidos-sub');
      if (!sub) return;
      sub.innerHTML = '';
      var btnTodos = document.createElement('button');
      btnTodos.type = 'button';
      btnTodos.setAttribute('data-loja', '');
      btnTodos.textContent = 'Todos';
      btnTodos.addEventListener('click', function () { irParaPedidos(''); });
      sub.appendChild(btnTodos);
      (data.lojas || []).forEach(function (nome) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.setAttribute('data-loja', nome);
        btn.textContent = nome;
        btn.addEventListener('click', function () { irParaPedidos(nome); });
        sub.appendChild(btn);
      });
    })
    .catch(function () {});
}

function irParaPedidos(loja) {
  pedidosLojaAtual = (loja === '' || loja === undefined) ? null : loja;
  var sub = document.getElementById('menu-pedidos-sub');
  if (sub) sub.classList.add('oculto');
  document.querySelectorAll('.menu button[data-pagina]').forEach(function (b) {
    b.classList.remove('ativo');
  });
  document.querySelectorAll('.menu-pedidos-sub button').forEach(function (b) {
    b.classList.remove('submenu-ativo');
    if ((b.getAttribute('data-loja') || '') === (pedidosLojaAtual || '')) b.classList.add('submenu-ativo');
  });
  var wrapper = document.getElementById('menu-pedidos-wrapper');
  if (wrapper) wrapper.classList.add('ativo');
  document.querySelectorAll('.pagina').forEach(function (p) { p.classList.add('oculto'); });
  var el = document.getElementById('pagina-pedidos');
  if (el) el.classList.remove('oculto');
  atualizarTituloPedidos();
  carregarPedidos();
}

function limparFiltrosPedidos() {
  var buscaInput = document.getElementById('busca-pedidos');
  if (buscaInput) buscaInput.value = '';
  filtroLojaSelecionado = null;
  pedidosLojaAtual = null;
  var sub = document.getElementById('menu-pedidos-sub');
  if (sub) {
    document.querySelectorAll('.menu-pedidos-sub button').forEach(function (b) {
      b.classList.remove('submenu-ativo');
      if ((b.getAttribute('data-loja') || '') === '') b.classList.add('submenu-ativo');
    });
  }
  atualizarTituloPedidos();
  carregarPedidos(1);
}

function atualizarTituloPedidos() {
  var titulo = document.getElementById('pedidos-titulo');
  if (!titulo) return;
  titulo.textContent = pedidosLojaAtual ? 'Pedidos em aberto - ' + pedidosLojaAtual : 'Pedidos em aberto';
}

// Dashboard
let graficoCanal = null;
let graficoDiario = null;

function carregarDashboard() {
  // Verificar se os elementos existem
  const acumuladoEl = document.getElementById('dashboard-acumulado-total');
  if (!acumuladoEl) return; // Se não estiver na página dashboard, não fazer nada
  
  // Mostrar loading
  acumuladoEl.textContent = 'Carregando...';
  
  api('/api/dashboard')
    .then(function (r) {
      return r.json();
    })
    .then(function (data) {
      const h = data.hoje || {};
      const o = data.ontem || {};
      const a = data.acumulado || {};
      const e = data.embalagens || {};
      
      // Métricas principais
      document.getElementById('dashboard-acumulado-total').textContent = a.total || 0;
      var acumuladoSub = document.getElementById('dashboard-acumulado-sub');
      if (acumuladoSub) acumuladoSub.textContent = (data.pedidos_abertos != null ? data.pedidos_abertos + ' pedidos em aberto' : 'Aguardando pedidos do mês');
      document.getElementById('dashboard-media-diaria').textContent = a.media_diaria || 0;
      document.getElementById('dashboard-dia-anterior').textContent = o.total_pedidos || 0;
      
      // Ideal Média Diária: valor gravado às 7:50 (pedidos em aberto do início do dia) ou ajuste manual; exibir o que a API envia
      const metaInput = document.getElementById('dashboard-ideal-media-input');
      const metaDisplay = document.getElementById('dashboard-ideal-media-display');
      const valorParaExibir = a.meta_diaria != null ? parseInt(a.meta_diaria, 10) : 180;
      if (metaInput.style.display !== 'inline-block') {
        metaInput.value = valorParaExibir;
        metaDisplay.textContent = valorParaExibir;
      }
      const metaParaCalculo = parseInt(metaInput.value, 10) || valorParaExibir;
      const percentualMeta = a.media_diaria != null && metaParaCalculo > 0
        ? ((a.media_diaria / metaParaCalculo) * 100).toFixed(1)
        : 0;
      document.getElementById('dashboard-percentual-meta').textContent = percentualMeta + '%';
      
      // Métricas secundárias
      document.getElementById('dashboard-pedidos-abertos').textContent = data.pedidos_abertos || 0;
      document.getElementById('dashboard-embalagens-usadas').textContent = e.usadas_mes || 0;
      var custoEmbEl = document.getElementById('dashboard-custo-embalagem-total');
      if (custoEmbEl) custoEmbEl.textContent = data.custo_embalagem_total_geral != null ? 'R$ ' + Number(data.custo_embalagem_total_geral).toFixed(2) : '-';
      
      // Tabela de embalagens detalhadas
      const embalagensDetalhadas = document.getElementById('dashboard-embalagens-detalhadas');
      if (e.detalhadas && e.detalhadas.length > 0) {
        let html = '<table><thead><tr><th>Embalagem</th><th>Quantidade</th><th>Custo Unitário (R$)</th><th>Valor Total (R$)</th></tr></thead><tbody>';
        e.detalhadas.forEach(function(emb) {
          html += '<tr>' +
            '<td><strong>' + (emb.nome || '-') + '</strong></td>' +
            '<td>' + (emb.quantidade || 0) + '</td>' +
            '<td>R$ ' + (emb.custo_unitario || 0).toFixed(2) + '</td>' +
            '<td>R$ ' + (emb.valor_total || 0).toFixed(2) + '</td>' +
            '</tr>';
        });
        html += '<tr style="font-weight: bold; background-color: #f0f0f0;"><td colspan="3">Total</td><td>R$ ' + (e.valor_total_mes || 0).toFixed(2) + '</td></tr>';
        html += '</tbody></table>';
        embalagensDetalhadas.innerHTML = html;
      } else {
        embalagensDetalhadas.innerHTML = '<p>Nenhuma embalagem utilizada no mês.</p>';
      }
      
      // Data de referência dos cards Por Canal e Gráfico por Canal (mês atual; reset dia 1)
      var porCanalDataStr = '';
      if (data.por_canal_data) {
        var parts = String(data.por_canal_data).split('-');
        if (parts.length >= 2) {
          var ano = parts[0];
          var mes = parts[1];
          porCanalDataStr = '(' + mes + '/' + ano + ')';
        }
      }
      var porCanalDataEl = document.getElementById('dashboard-por-canal-data');
      var graficoCanalDataEl = document.getElementById('dashboard-grafico-canal-data');
      if (porCanalDataEl) porCanalDataEl.textContent = porCanalDataStr;
      if (graficoCanalDataEl) graficoCanalDataEl.textContent = porCanalDataStr;

      // Mês de referência do card Embalagens Utilizadas
      var embalagensMesStr = '';
      if (data.embalagens_mes_ref) {
        var p = String(data.embalagens_mes_ref).split('-');
        if (p.length >= 2) embalagensMesStr = '(' + p[1] + '/' + p[0] + ')';
      }
      var embalagensMesEl = document.getElementById('dashboard-embalagens-mes-ref');
      if (embalagensMesEl) embalagensMesEl.textContent = embalagensMesStr;

      // Cards fixos por canal: Tray sempre primeiro; sem Ifood e Loja Física
      const CANAIS_FIXOS = ['Tray', 'TikTok', 'Shopee', 'Mercado Livre', 'Shein', 'Época', 'Pedidos Internos', 'BLZWEB'];
      const porCanalMap = {};
      if (data.por_canal && data.por_canal.length > 0) {
        data.por_canal.forEach(function(item) {
          var nome = (item.canal || '').trim();
          if (nome) porCanalMap[nome] = item;
        });
      }
      const containerCardsCanal = document.getElementById('dashboard-cards-canal');
      if (!containerCardsCanal) return;
      let html = '';
      CANAIS_FIXOS.forEach(function(canal) {
        const item = porCanalMap[canal] || { quantidade: 0, frete_total: 0, frete_real_total: 0, custo_embalagem_total: 0, ganho_perda_liquido: 0, ganho_perda_medio: 0 };
        const isTray = (canal + '').toLowerCase() === 'tray';
        html += '<div class="dashboard-card-canal' + (isTray ? ' dashboard-card-canal--tray' : '') + '">';
        html += '<h4 class="dashboard-card-canal-titulo">' + canal + '</h4>';
        if (isTray) {
          const ganhoPerdaLiquido = item.ganho_perda_liquido || 0;
          const ganhoPerdaMedio = item.ganho_perda_medio != null ? item.ganho_perda_medio : 0;
          const classeGanhoPerda = ganhoPerdaLiquido >= 0 ? 'positivo' : 'negativo';
          const classeMedia = ganhoPerdaMedio >= 0 ? 'positivo' : 'negativo';
          html += '<table><thead><tr><th>Qtd</th><th>Pago Cliente</th><th>Pago Transportadora</th><th>Custo embalagem</th><th>Custo Total</th><th>Média Custo Total</th></tr></thead><tbody>';
          html += '<tr>' +
            '<td>' + (item.quantidade || 0) + '</td>' +
            '<td>R$ ' + (item.frete_total || 0).toFixed(2) + '</td>' +
            '<td>R$ ' + (item.frete_real_total || 0).toFixed(2) + '</td>' +
            '<td>R$ ' + (item.custo_embalagem_total != null ? item.custo_embalagem_total : 0).toFixed(2) + '</td>' +
            '<td class="' + classeGanhoPerda + '">R$ ' + ganhoPerdaLiquido.toFixed(2) + '</td>' +
            '<td class="' + classeMedia + '">R$ ' + ganhoPerdaMedio.toFixed(2) + '</td>' +
            '</tr>';
          html += '</tbody></table>';
        } else {
          html += '<table><thead><tr><th>Qtd</th><th>Custo embalagem</th></tr></thead><tbody>';
          html += '<tr>' +
            '<td>' + (item.quantidade || 0) + '</td>' +
            '<td>R$ ' + (item.custo_embalagem_total != null ? item.custo_embalagem_total : 0).toFixed(2) + '</td>' +
            '</tr>';
          html += '</tbody></table>';
        }
        html += '</div>';
      });
      containerCardsCanal.innerHTML = html;
      
      // Gráfico por canal (pizza)
      atualizarGraficoCanal(data.por_canal || []);
      
      // Gráfico diário (barras) - usar meta atual do input
      const metaParaGrafico = parseInt(metaInput.value, 10) || valorParaExibir;
      atualizarGraficoDiario(data.grafico_diario || [], metaParaGrafico);
    })
    .catch(function (err) {
      console.error('Erro ao carregar dashboard:', err);
      document.getElementById('dashboard-acumulado-total').textContent = 'Erro';
    });
}

function atualizarGraficoCanal(dadosCanal) {
  const ctx = document.getElementById('grafico-canal');
  if (!ctx) return;
  
  // Destruir gráfico anterior se existir
  if (graficoCanal) {
    graficoCanal.destroy();
  }
  
  const labels = dadosCanal.map(item => item.canal || 'Não identificado');
  const valores = dadosCanal.map(item => item.quantidade);
  
  // Calcular total para percentuais
  const total = valores.reduce((a, b) => a + b, 0);
  
  graficoCanal = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        data: valores,
        backgroundColor: [
          '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
          '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1'
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'right',
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.parsed || 0;
              const percent = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
              return label + ': ' + value + ' (' + percent + '%)';
            }
          }
        }
      }
    }
  });
}

function exportarDashboardExcel() {
  api('/api/dashboard/excel')
    .then(function (r) {
      if (!r.ok) return r.json().then(function (e) { throw new Error(e.erro || 'Erro ao exportar'); });
      return r.blob();
    })
    .then(function (blob) {
      var a = document.createElement('a');
      a.href = window.URL.createObjectURL(blob);
      a.download = 'dashboard-' + (new Date().toISOString().slice(0, 10)) + '.xlsx';
      a.click();
      window.URL.revokeObjectURL(a.href);
    })
    .catch(function (e) {
      alert(e.message || 'Erro ao exportar Excel.');
    });
}

function imprimirRelatorios() {
  window.print();
}

function atualizarGraficoDiario(dadosDiarios, metaDiaria) {
  const ctx = document.getElementById('grafico-diario');
  if (!ctx) return;
  
  if (graficoDiario) {
    graficoDiario.destroy();
  }
  
  // Eixo X: dias do mês em sequência (1, 2, 3, ... 31)
  const labels = (dadosDiarios && dadosDiarios.length) ? dadosDiarios.map(item => item.dia != null ? item.dia : (new Date(item.data)).getDate()) : [];
  const valores = (dadosDiarios && dadosDiarios.length) ? dadosDiarios.map(item => item.quantidade || 0) : [];
  const metaNum = parseInt(metaDiaria, 10) || 0;
  const metaArray = new Array(labels.length).fill(metaNum);
  
  const maxVal = Math.max(...valores, metaNum, 0);
  const stepY = maxVal <= 20 ? 5 : maxVal <= 100 ? 20 : 50;
  
  graficoDiario = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Pedidos finalizados',
          data: valores,
          backgroundColor: '#3B82F6',
          borderColor: '#2563EB',
          borderWidth: 1
        },
        {
          label: 'Meta Diária',
          data: metaArray,
          type: 'line',
          borderColor: '#10B981',
          borderWidth: 2,
          fill: false,
          pointRadius: 0,
          tension: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      scales: {
        x: {
          title: { display: true, text: 'Dia do mês' },
          ticks: {
            autoSkip: false,
            maxRotation: 0,
            minRotation: 0
          }
        },
        y: {
          beginAtZero: true,
          suggestedMax: maxVal > 0 ? maxVal + stepY : metaNum + stepY,
          ticks: {
            stepSize: stepY
          },
          title: { display: true, text: 'Quantidade' }
        }
      },
      plugins: {
        legend: {
          display: true,
          position: 'top'
        }
      }
    }
  });
}

// Pedidos
let timeoutBuscaPedidos = null;

function mostrarFiltroLoja(event) {
  event.stopPropagation();
  
  // Remover dropdown existente se houver
  var dropdownExistente = document.getElementById('dropdown-filtro-loja');
  if (dropdownExistente) {
    dropdownExistente.remove();
    return;
  }
  
  // Criar dropdown
  var dropdown = document.createElement('div');
  dropdown.id = 'dropdown-filtro-loja';
  dropdown.className = 'dropdown-filtro-loja';
  
  // Opção "Todas"
  var opcaoTodas = document.createElement('div');
  opcaoTodas.className = 'dropdown-item' + (filtroLojaSelecionado === null ? ' ativo' : '');
  opcaoTodas.textContent = 'Todas';
  opcaoTodas.onclick = function(e) {
    e.stopPropagation();
    filtroLojaSelecionado = null;
    carregarPedidos();
    dropdown.remove();
  };
  dropdown.appendChild(opcaoTodas);
  
  // Opções de lojas
  LOJAS_DISPONIVEIS.forEach(function(loja) {
    var opcao = document.createElement('div');
    opcao.className = 'dropdown-item' + (filtroLojaSelecionado === loja ? ' ativo' : '');
    opcao.textContent = loja;
    opcao.onclick = function(e) {
      e.stopPropagation();
      filtroLojaSelecionado = loja;
      carregarPedidos();
      dropdown.remove();
    };
    dropdown.appendChild(opcao);
  });
  
  // Posicionar dropdown
  var th = event.currentTarget;
  var rect = th.getBoundingClientRect();
  dropdown.style.position = 'fixed';
  dropdown.style.top = (rect.bottom + window.scrollY) + 'px';
  dropdown.style.left = rect.left + 'px';
  dropdown.style.minWidth = rect.width + 'px';
  
  document.body.appendChild(dropdown);
  
  // Fechar ao clicar fora
  setTimeout(function() {
    document.addEventListener('click', function fecharDropdown() {
      dropdown.remove();
      document.removeEventListener('click', fecharDropdown);
    }, { once: true });
  }, 0);
}

function filtrarPedidosPorLoja(lista) {
  if (!filtroLojaSelecionado) {
    return lista;
  }
  
  return lista.filter(function(p) {
    return p.loja_nome === filtroLojaSelecionado;
  });
}

function carregarPedidos(pagina) {
  if (pagina != null) pagePedidos = Math.max(1, parseInt(pagina, 10) || 1);
  var container = document.getElementById('pedidos-lista');
  if (!container) return;
  container.innerHTML = '<p>Carregando...</p>';

  var buscaInput = document.getElementById('busca-pedidos');
  var termoBusca = buscaInput ? buscaInput.value.trim() : '';
  var params = ['page=' + pagePedidos, 'per_page=' + PER_PAGE];
  if (pedidosLojaAtual) params.push('marketplace=' + encodeURIComponent(pedidosLojaAtual));
  if (filtroLojaSelecionado) params.push('loja=' + encodeURIComponent(filtroLojaSelecionado));
  if (termoBusca) params.push('busca=' + encodeURIComponent(termoBusca));
  var url = '/api/pedidos?' + params.join('&');

  api(url)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var lista = data.pedidos || [];
      var total = data.total != null ? data.total : lista.length;
      var totalPages = data.total_pages != null ? data.total_pages : 1;
      var ultimaSync = data.ultima_sincronizacao;

      if (!lista || !lista.length) {
        container.innerHTML = '<p>Nenhum pedido em aberto' + (termoBusca ? ' para "' + termoBusca + '"' : '') + '.</p>';
        if (ultimaSync) {
          var dataSync = new Date(ultimaSync);
          var minutosAtras = Math.floor((new Date() - dataSync) / 60000);
          container.innerHTML += '<p style="font-size: 0.9em; color: #666; margin-top: 0.5rem;">Última sincronização: ' + (minutosAtras < 1 ? 'agora' : minutosAtras + ' min atrás') + '</p>';
        }
        atualizarMetricasPedidos(0);
        renderizarPaginacaoPedidos(0, 0, 0);
        return;
      }

      atualizarMetricasPedidos(total);
      var indicadorLoja = filtroLojaSelecionado ? ' (Filtrado: ' + filtroLojaSelecionado + ')' : '';
      var classeThLoja = 'coluna-filtravel';
      var isAdmin = usuario && usuario.categoria === 'ADMIN';

      var html = '<table><thead><tr><th>Nº Pedido</th><th>Canal de venda</th><th class="' + classeThLoja + '" onclick="mostrarFiltroLoja(event)">Loja' + indicadorLoja + ' ▼</th><th>Ações</th></tr></thead><tbody>';
      lista.forEach(function (p) {
        var num = (p.numero_pedido || '').replace(/'/g, "\\'");
        html += '<tr><td>' + (p.numero_pedido || '-') + '</td><td>' + (p.numero_loja || '-') + '</td><td>' + (p.loja_nome || '-') + '</td><td>';
        html += '<button type="button" class="btn-acao" onclick="abrirModalFinalizar(\'' + num + '\')">Finalizar Pedido</button>';
        if (isAdmin) {
          html += ' <button type="button" class="btn-acao btn-excluir" onclick="excluirPedido(\'' + num + '\')" title="Excluir (só admin)">Excluir</button>';
        }
        html += '</td></tr>';
      });
      html += '</tbody></table>';
      if (ultimaSync) {
        var dataSync = new Date(ultimaSync);
        var minutosAtras = Math.floor((new Date() - dataSync) / 60000);
        html += '<p style="font-size: 0.9em; color: #666; margin-top: 0.5rem; text-align: right;">Última sincronização: ' + (minutosAtras < 1 ? 'agora' : minutosAtras + ' min atrás') + '</p>';
      }
      container.innerHTML = html;
      var inicio = (pagePedidos - 1) * PER_PAGE + 1;
      var fim = Math.min(pagePedidos * PER_PAGE, total);
      var infoEl = document.getElementById('pedidos-info-registros');
      if (infoEl) {
        infoEl.classList.remove('oculto');
        infoEl.textContent = 'Mostrando ' + inicio + ' até ' + fim + ' de ' + total + ' pedidos em aberto';
      }
      renderizarPaginacaoPedidos(pagePedidos, totalPages, total);
    })
    .catch(function () {
      container.innerHTML = '<p class="erro">Erro ao carregar pedidos.</p>';
      atualizarMetricasPedidos(0);
      renderizarPaginacaoPedidos(1, 1, 0);
    });
}

function renderizarPaginacaoPedidos(paginaAtual, totalPaginas, total) {
  var el = document.getElementById('paginacao-pedidos');
  if (!el) return;
  if (totalPaginas <= 1 && total <= PER_PAGE) {
    el.innerHTML = '';
    return;
  }
  var html = '<div class="paginacao"><span>Página ' + paginaAtual + ' de ' + totalPaginas + '</span> ';
  if (paginaAtual > 1) {
    html += '<button type="button" class="btn-secundario" onclick="carregarPedidos(' + (paginaAtual - 1) + ')">Anterior</button> ';
  }
  if (paginaAtual < totalPaginas) {
    html += '<button type="button" class="btn-secundario" onclick="carregarPedidos(' + (paginaAtual + 1) + ')">Próxima</button>';
  }
  html += '</div>';
  el.innerHTML = html;
}

function excluirPedido(numero) {
  if (!confirm('Excluir o pedido ' + numero + '? Esta ação não pode ser desfeita.')) return;
  api('/api/pedidos/' + encodeURIComponent(numero), { method: 'DELETE' })
    .then(function (r) {
      if (!r.ok) return r.json().then(function (d) { throw new Error(d.erro || 'Erro ao excluir'); });
      carregarPedidos();
      carregarFinalizados();
      carregarDashboard();
    })
    .catch(function (e) {
      alert(e.message || 'Erro ao excluir pedido.');
    });
}

function atualizarMetricasPedidos(total) {
  var elTotal = document.getElementById('pedidos-metrica-total');
  if (elTotal) elTotal.textContent = total;
}


function sincronizarPedidos() {
  // Forçar sincronização passando sincronizar=1
  var url = '/api/pedidos?sincronizar=1';
  if (pedidosLojaAtual) url += '&marketplace=' + encodeURIComponent(pedidosLojaAtual);
  
  var container = document.getElementById('pedidos-lista');
  if (container) container.innerHTML = '<p>Sincronizando com Bling... Isso pode levar alguns minutos.</p>';
  
  api(url)
    .then(function (r) {
      return r.json();
    })
    .then(function (data) {
      // Recarregar a lista normalmente (sem sincronizar novamente)
      carregarPedidos();
      alert('Sincronização concluída. Os pedidos foram atualizados.');
    })
    .catch(function (err) {
      if (container) container.innerHTML = '<p class="erro">Erro ao sincronizar.</p>';
      alert('Erro ao sincronizar com o Bling.');
    });
}

let pedidoEmFinalizacao = null;
let pedidoReservado = false;
let blingInfoObtida = false; // Flag para controlar se o botão "Obter informações" foi clicado

var dadosBlingAdicionar = null; // Resposta do Bling ao buscar por ID (para enviar id_bling, loja_id no POST)
// Adicionar pedido manual: passo 1 = informar ID Bling e buscar; passo 2 = revisar e adicionar
function abrirModalAdicionarPedido() {
  dadosBlingAdicionar = null;
  document.getElementById('modal-adicionar-id-bling').value = '';
  document.getElementById('modal-adicionar-numero').value = '';
  document.getElementById('modal-adicionar-marketplace').value = '';
  document.getElementById('modal-adicionar-frete').value = '';
  document.getElementById('modal-adicionar-aviso').classList.add('oculto');
  document.getElementById('modal-adicionar-aviso2').classList.add('oculto');
  document.getElementById('modal-adicionar-step1').style.display = 'block';
  document.getElementById('modal-adicionar-step2').style.display = 'none';
  document.getElementById('modal-adicionar-pedido').classList.remove('oculto');
}

function voltarModalAdicionarStep1() {
  document.getElementById('modal-adicionar-step1').style.display = 'block';
  document.getElementById('modal-adicionar-step2').style.display = 'none';
}

function fecharModalAdicionar() {
  document.getElementById('modal-adicionar-pedido').classList.add('oculto');
  document.getElementById('modal-adicionar-step1').style.display = 'block';
  document.getElementById('modal-adicionar-step2').style.display = 'none';
  carregarPedidos();
}

function buscarDadosBlingAdicionar() {
  var idBling = document.getElementById('modal-adicionar-id-bling').value.trim();
  var avisoEl = document.getElementById('modal-adicionar-aviso');
  avisoEl.classList.add('oculto');
  if (!idBling) {
    avisoEl.textContent = 'Informe o ID do pedido no Bling.';
    avisoEl.classList.remove('oculto');
    return;
  }
  avisoEl.textContent = 'Buscando dados no Bling...';
  avisoEl.style.color = '#0066cc';
  avisoEl.classList.remove('oculto');
  api('/api/pedidos/bling/' + encodeURIComponent(idBling))
    .then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.erro || 'Pedido não encontrado no Bling.');
        return d;
      });
    })
    .then(function (d) {
      dadosBlingAdicionar = d;
      document.getElementById('modal-adicionar-numero').value = d.numero_pedido || '';
      document.getElementById('modal-adicionar-marketplace').value = (d.loja_nome || d.marketplace || '').trim() || 'site';
      document.getElementById('modal-adicionar-frete').value = (d.frete_cliente != null ? Number(d.frete_cliente) : 0);
      document.getElementById('modal-adicionar-step1').style.display = 'none';
      document.getElementById('modal-adicionar-step2').style.display = 'block';
      avisoEl.classList.add('oculto');
    })
    .catch(function (e) {
      avisoEl.textContent = e.message || 'Erro ao buscar no Bling.';
      avisoEl.style.color = '#c00';
    });
}

function confirmarAdicionarPedido() {
  var numero = document.getElementById('modal-adicionar-numero').value.trim();
  var marketplace = document.getElementById('modal-adicionar-marketplace').value.trim();
  var frete = parseFloat(document.getElementById('modal-adicionar-frete').value) || 0;
  var avisoEl = document.getElementById('modal-adicionar-aviso2');
  avisoEl.classList.add('oculto');
  if (!numero || !marketplace) {
    avisoEl.textContent = 'Número do pedido e marketplace são obrigatórios.';
    avisoEl.classList.remove('oculto');
    return;
  }
  var payload = { numero_pedido: numero, marketplace: marketplace, frete_cliente: frete };
  if (dadosBlingAdicionar) {
    if (dadosBlingAdicionar.id_bling) payload.id_bling = dadosBlingAdicionar.id_bling;
    if (dadosBlingAdicionar.loja_id != null) payload.loja_id = dadosBlingAdicionar.loja_id;
    if (dadosBlingAdicionar.numero_loja) payload.numero_loja = dadosBlingAdicionar.numero_loja;
  }
  api('/api/pedidos', {
    method: 'POST',
    body: JSON.stringify(payload)
  })
    .then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.erro || 'Erro ao adicionar pedido.');
        return d;
      });
    })
    .then(function () {
      fecharModalAdicionar();
      alert('Pedido adicionado com sucesso!');
    })
    .catch(function (e) {
      avisoEl.textContent = e.message || 'Erro ao adicionar pedido.';
      avisoEl.classList.remove('oculto');
    });
}

function abrirModalFinalizar(numeroPedido) {
  pedidoEmFinalizacao = numeroPedido;
  pedidoReservado = false;
  blingInfoObtida = false; // Resetar flag ao abrir modal
  document.getElementById('modal-pedido-num').textContent = numeroPedido;
  document.getElementById('modal-observacoes').value = '';
  document.getElementById('modal-finalizar-frete').value = '';
  document.getElementById('modal-finalizar-peso').value = '';
  document.getElementById('modal-finalizar-tracking').value = '';
  document.getElementById('modal-finalizar-marketplace').value = '';
  document.getElementById('modal-finalizar-transportadora').value = '';
  var custoEl = document.getElementById('modal-finalizar-custo-mandae');
  if (custoEl) custoEl.value = '';
  var avisoEl = document.getElementById('modal-finalizar-aviso');
  avisoEl.classList.add('oculto');
  
  // Mostrar modal
  var modal = document.getElementById('modal-finalizar');
  modal.classList.remove('oculto');
  
  // Tentar reservar o pedido
  avisoEl.textContent = 'Reservando pedido...';
  avisoEl.classList.remove('oculto');
  avisoEl.style.color = '#0066cc';
  
  api('/api/pedidos/' + encodeURIComponent(numeroPedido) + '/reservar', {
    method: 'POST'
  })
    .then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok) {
          throw new Error(data.erro || 'Erro ao reservar pedido');
        }
        return data;
      });
    })
    .then(function (data) {
      pedidoReservado = true;
      avisoEl.classList.add('oculto');
      // Continuar carregando os dados do pedido
      carregarDadosModalFinalizar(numeroPedido);
    })
    .catch(function (err) {
      avisoEl.textContent = err.message || 'Erro ao reservar pedido.';
      avisoEl.classList.remove('oculto');
      avisoEl.style.color = '#cc0000';
      // Mesmo com erro na reserva, tentar carregar os dados (pode ser que o usuário seja admin)
      carregarDadosModalFinalizar(numeroPedido);
    });
}

// Variável global para armazenar lista de embalagens disponíveis
var embalagensDisponiveisGlobal = [];

// Funções para gerenciar múltiplas embalagens (definidas antes de serem usadas)
function adicionarEmbalagemItem(embalagemIdSelecionada, quantidade, embalagens) {
  var container = document.getElementById('embalagens-container');
  if (!container) return;
  
  // Armazenar embalagens globalmente
  if (embalagens) {
    embalagensDisponiveisGlobal = embalagens;
  }
  
  var index = container.children.length;
  var itemDiv = document.createElement('div');
  itemDiv.className = 'embalagem-item';
  itemDiv.style.marginBottom = '0.5rem';
  itemDiv.style.display = 'flex';
  itemDiv.style.alignItems = 'center';
  
  var select = document.createElement('select');
  select.className = 'select-embalagem-item';
  select.setAttribute('data-index', index);
  select.innerHTML = '<option value="">Selecione uma embalagem</option>';
  
  // Popular opções
  (embalagensDisponiveisGlobal || []).forEach(function(e) {
    var option = document.createElement('option');
    option.value = e.id;
    option.textContent = (e.nome || '') + ' (R$ ' + (e.custo != null ? Number(e.custo).toFixed(2) : '') + ')';
    if (embalagemIdSelecionada && e.id == embalagemIdSelecionada) {
      option.selected = true;
    }
    select.appendChild(option);
  });
  
  var qtdInput = document.createElement('input');
  qtdInput.type = 'number';
  qtdInput.className = 'quantidade-embalagem-item';
  qtdInput.setAttribute('data-index', index);
  qtdInput.min = 1;
  qtdInput.value = quantidade || 1;
  qtdInput.step = 1;
  qtdInput.placeholder = 'Qtd';
  qtdInput.style.width = '80px';
  qtdInput.style.marginLeft = '0.5rem';
  
  var btnRemover = document.createElement('button');
  btnRemover.type = 'button';
  btnRemover.className = 'btn-remover-embalagem';
  btnRemover.setAttribute('data-index', index);
  btnRemover.textContent = '✕';
  btnRemover.onclick = function() { removerEmbalagemItem(index); };
  btnRemover.style.marginLeft = '0.5rem';
  btnRemover.style.display = index === 0 ? 'none' : 'inline-block';
  
  itemDiv.appendChild(select);
  itemDiv.appendChild(qtdInput);
  itemDiv.appendChild(btnRemover);
  container.appendChild(itemDiv);
  
  // Atualizar visibilidade dos botões de remover
  atualizarVisibilidadeBotoesRemover();
}

function removerEmbalagemItem(index) {
  var container = document.getElementById('embalagens-container');
  if (!container || container.children.length <= 1) return; // Não remover se for o último
  
  var item = container.children[index];
  if (item) {
    container.removeChild(item);
    // Reindexar
    atualizarIndicesEmbalagens();
  }
}

function atualizarIndicesEmbalagens() {
  var container = document.getElementById('embalagens-container');
  if (!container) return;
  
  Array.from(container.children).forEach(function(item, index) {
    var select = item.querySelector('.select-embalagem-item');
    var qtdInput = item.querySelector('.quantidade-embalagem-item');
    var btnRemover = item.querySelector('.btn-remover-embalagem');
    
    if (select) select.setAttribute('data-index', index);
    if (qtdInput) qtdInput.setAttribute('data-index', index);
    if (btnRemover) {
      btnRemover.setAttribute('data-index', index);
      btnRemover.onclick = function() { removerEmbalagemItem(index); };
    }
  });
  
  atualizarVisibilidadeBotoesRemover();
}

function atualizarVisibilidadeBotoesRemover() {
  var container = document.getElementById('embalagens-container');
  if (!container) return;
  
  Array.from(container.children).forEach(function(item, index) {
    var btnRemover = item.querySelector('.btn-remover-embalagem');
    if (btnRemover) {
      btnRemover.style.display = container.children.length > 1 ? 'inline-block' : 'none';
    }
  });
}

function coletarEmbalagensDoForm() {
  var container = document.getElementById('embalagens-container');
  if (!container) return [];
  
  var embalagens = [];
  Array.from(container.children).forEach(function(item) {
    var select = item.querySelector('.select-embalagem-item');
    var qtdInput = item.querySelector('.quantidade-embalagem-item');
    
    if (select && select.value && qtdInput) {
      var id = parseInt(select.value, 10);
      var qtd = parseInt(qtdInput.value, 10) || 1;
      if (id && qtd >= 1) {
        embalagens.push({
          embalagem_id: id,
          quantidade: qtd
        });
      }
    }
  });
  
  return embalagens;
}

function carregarDadosModalFinalizar(numeroPedido) {

  function preencherForm(d, embalagens, lojas) {
    // Preencher marketplace como texto
    var mktInput = document.getElementById('modal-finalizar-marketplace');
    if (mktInput) {
      mktInput.value = d.marketplace || '';
    }
    
    // Preencher com dados do banco
    document.getElementById('modal-finalizar-frete').value = d.frete_cliente != null ? Number(d.frete_cliente) : '';
    var pesoInput = document.getElementById('modal-finalizar-peso');
    if (pesoInput) {
      pesoInput.value = d.peso != null ? Number(d.peso) : '';
    }
    var transpInput = document.getElementById('modal-finalizar-transportadora');
    if (transpInput) {
      transpInput.value = d.transportadora || '';
    }
    document.getElementById('modal-finalizar-tracking').value = d.tracking_code || '';
    
    // Popular selects de embalagens
    var embalagensContainer = document.getElementById('embalagens-container');
    if (embalagensContainer) {
      // Limpar container
      embalagensContainer.innerHTML = '';
      
      // Se o pedido já tem embalagens, carregar elas
      var embalagensExistentes = d.embalagens && d.embalagens.length > 0 ? d.embalagens : [];
      
      // Se não tem embalagens mas tem embalagem antiga (compatibilidade)
      if (embalagensExistentes.length === 0 && d.embalagem) {
        embalagensExistentes = [{
          embalagem: d.embalagem,
          quantidade: d.quantidade_embalagem || 1
        }];
      }
      
      // Se não tem nenhuma embalagem, criar um item vazio
      if (embalagensExistentes.length === 0) {
        embalagensExistentes = [{}];
      }
      
      // Criar itens de embalagem
      embalagensExistentes.forEach(function(embItem, index) {
        var embId = null;
        var qtd = 1;
        if (embItem.embalagem) {
          embId = embItem.embalagem.id || embItem.embalagem_id;
          qtd = embItem.quantidade || 1;
        }
        adicionarEmbalagemItem(embId, qtd, embalagens);
      });
    }
  }

  // Buscar apenas dados do banco, embalagens e lojas (sem buscar Bling automaticamente)
  Promise.all([
    api('/api/pedidos/' + encodeURIComponent(numeroPedido) + '/detalhes').then(function (r) { return r.json(); }),
    api('/api/embalagens?status=ativo').then(function (r) { return r.json(); }),
    api('/api/pedidos/lojas').then(function (r) { return r.json(); }).then(function (data) { return data.lojas || []; })
  ])
    .then(function (results) {
      preencherForm(results[0], results[1], results[2]);
    })
    .catch(function (err) {
      var avisoEl = document.getElementById('modal-finalizar-aviso');
      avisoEl.textContent = 'Erro ao carregar dados do pedido. ' + (err.message || '');
      avisoEl.classList.remove('oculto');
      avisoEl.style.color = '#cc0000';
    });
}

function obterInformacoesBling() {
  if (!pedidoEmFinalizacao) {
    alert('Nenhum pedido selecionado.');
    return;
  }

  var avisoEl = document.getElementById('modal-finalizar-aviso');
  avisoEl.textContent = 'Buscando detalhes do pedido no Bling...';
  avisoEl.classList.remove('oculto');
  avisoEl.style.color = '#0066cc';

  api('/api/pedidos/' + encodeURIComponent(pedidoEmFinalizacao) + '/detalhes-bling')
    .then(function (r) {
      if (!r.ok) {
        return r.json().then(function (data) {
          throw new Error(data.erro || 'Erro ao buscar detalhes do Bling');
        });
      }
      return r.json();
    })
    .then(function (detalhesBling) {
      blingInfoObtida = true; // Obrigatoriedade global: só permite finalizar após clicar em "Obter informações"

      if (!detalhesBling) {
        avisoEl.textContent = 'Nenhuma informação adicional encontrada no Bling.';
        avisoEl.style.color = '#666';
        return;
      }

      // Debug: verificar o que está vindo do backend
      console.log('Detalhes do Bling recebidos:', detalhesBling);

      var camposPreenchidos = [];

      // Preencher frete do Bling se disponível
      if (detalhesBling.frete != null && detalhesBling.frete !== '') {
        document.getElementById('modal-finalizar-frete').value = Number(detalhesBling.frete);
        camposPreenchidos.push('Frete');
      }
      
      // Preencher código de rastreamento do Bling se disponível
      var codigoRastreamento = detalhesBling.codigo_rastreamento;
      if (codigoRastreamento != null && codigoRastreamento !== '' && codigoRastreamento !== undefined) {
        document.getElementById('modal-finalizar-tracking').value = String(codigoRastreamento);
        camposPreenchidos.push('Código de rastreamento');
      }
      
      // Preencher transportadora (contato_nome que agora contém volumes.servico) se disponível
      var transpInput = document.getElementById('modal-finalizar-transportadora');
      var servico = detalhesBling.contato_nome; // Este campo agora contém volumes.servico
      if (servico != null && servico !== '' && servico !== undefined && transpInput) {
        transpInput.value = String(servico);
        camposPreenchidos.push('Transportadora');
      }
      
      // Preencher marketplace (numero_loja ou loja_id) se disponível
      var mktInput = document.getElementById('modal-finalizar-marketplace');
      if (mktInput) {
        if (detalhesBling.numero_loja != null && detalhesBling.numero_loja !== '' && detalhesBling.numero_loja !== undefined) {
          mktInput.value = String(detalhesBling.numero_loja);
          camposPreenchidos.push('Marketplace');
        } else if (detalhesBling.loja_id != null && detalhesBling.loja_id !== '' && detalhesBling.loja_id !== undefined) {
          mktInput.value = String(detalhesBling.loja_id);
          camposPreenchidos.push('Marketplace');
        }
      }

      if (camposPreenchidos.length > 0) {
        avisoEl.textContent = 'Informações obtidas do Bling: ' + camposPreenchidos.join(', ') + '.';
        avisoEl.style.color = '#006600';
      } else {
        avisoEl.textContent = 'Nenhuma informação adicional encontrada no Bling para este pedido.';
        avisoEl.style.color = '#666';
      }
    })
    .catch(function (err) {
      avisoEl.textContent = 'Erro ao buscar informações do Bling: ' + (err.message || 'Erro desconhecido');
      avisoEl.classList.remove('oculto');
      avisoEl.style.color = '#cc0000';
    });
}

function fecharModal() {
  // Remover reserva se o pedido foi reservado
  if (pedidoReservado && pedidoEmFinalizacao) {
    api('/api/pedidos/' + encodeURIComponent(pedidoEmFinalizacao) + '/reservar', {
      method: 'DELETE'
    })
      .then(function (r) {
        return r.json();
      })
      .catch(function (err) {
        // Ignorar erros ao remover reserva (pode ser que já tenha sido removida)
        console.log('Erro ao remover reserva:', err);
      });
  }
  
  document.getElementById('modal-finalizar').classList.add('oculto');
  pedidoEmFinalizacao = null;
  pedidoReservado = false;
  blingInfoObtida = false;
}

// Modal Visualização / preenchimento manual do pedido
function abrirModalVisualizar(numeroPedido) {
  var modal = document.getElementById('modal-visualizar-pedido');
  var numEl = document.getElementById('modal-visualizar-num');
  var numInput = document.getElementById('modal-visualizar-numero');
  var avisoEl = document.getElementById('modal-visualizar-aviso');
  numEl.textContent = numeroPedido;
  if (numInput) numInput.value = numeroPedido;
  avisoEl.classList.add('oculto');
  modal.classList.remove('oculto');

  function preencherForm(d) {
    var sel = document.getElementById('modal-visualizar-marketplace');
    if (sel && sel.options.length <= 1) {
      api('/api/pedidos/lojas').then(function (r) { return r.json(); }).then(function (data) {
        sel.innerHTML = '<option value="site">Selecione...</option>' +
          (data.lojas || []).map(function (nome) {
            return '<option value="' + (nome.replace(/"/g, '&quot;')) + '">' + nome + '</option>';
          }).join('');
        sel.value = d.marketplace || 'site';
      }).catch(function () { sel.value = d.marketplace || 'site'; });
    } else if (sel) {
      sel.value = d.marketplace || 'site';
    }
    document.getElementById('modal-visualizar-frete').value = d.frete_cliente != null ? Number(d.frete_cliente) : '';
    var transpSel = document.getElementById('modal-visualizar-transportadora');
    if (transpSel) transpSel.value = d.transportadora || '';
    document.getElementById('modal-visualizar-tracking').value = d.tracking_code || '';
  }

  api('/api/pedidos/' + encodeURIComponent(numeroPedido) + '/detalhes')
    .then(function (r) { return r.json(); })
    .then(preencherForm)
    .catch(function (e) {
      avisoEl.textContent = e.message || 'Erro ao carregar pedido.';
      avisoEl.classList.remove('oculto');
    });
}

function salvarDadosPedido() {
  var numInput = document.getElementById('modal-visualizar-numero');
  var numero = numInput ? numInput.value : '';
  if (!numero) return;
  var avisoEl = document.getElementById('modal-visualizar-aviso');
  avisoEl.classList.add('oculto');

  var marketplace = document.getElementById('modal-visualizar-marketplace').value || 'site';
  var frete = parseFloat(document.getElementById('modal-visualizar-frete').value) || 0;
  var transpSel = document.getElementById('modal-visualizar-transportadora');
  var transportadora = (transpSel && transpSel.value) ? transpSel.value.trim() : null;
  if (transportadora === '') transportadora = null;
  var tracking = document.getElementById('modal-visualizar-tracking').value.trim() || null;

  api('/api/pedidos/' + encodeURIComponent(numero), {
    method: 'PUT',
    body: JSON.stringify({
      marketplace: marketplace,
      frete_cliente: frete,
      transportadora: transportadora,
      tracking_code: tracking
    })
  })
    .then(function (r) { return r.json().then(function (d) { if (!r.ok) throw new Error(d.erro || 'Erro ao salvar.'); return d; }); })
    .then(function () {
      fecharModalVisualizar();
      alert('Dados salvos. Agora você pode finalizar o pedido.');
    })
    .catch(function (e) {
      avisoEl.textContent = e.message || 'Erro ao salvar.';
      avisoEl.classList.remove('oculto');
    });
}

function fecharModalVisualizar() {
  document.getElementById('modal-visualizar-pedido').classList.add('oculto');
  carregarPedidos();
}

function ordenarFinalizados(col) {
  if (orderByFinalizados === col) {
    sortDirFinalizados = sortDirFinalizados === 'asc' ? 'desc' : 'asc';
  } else {
    orderByFinalizados = col;
    sortDirFinalizados = 'desc';
  }
  carregarFinalizados(1);
}

// Aba Finalizados
function carregarFinalizados(pagina) {
  if (pagina != null) pageFinalizados = Math.max(1, parseInt(pagina, 10) || 1);
  var container = document.getElementById('finalizados-lista');
  if (!container) return;
  container.innerHTML = '<p>Carregando...</p>';

  var buscaInput = document.getElementById('busca-finalizados');
  var termoBusca = buscaInput ? buscaInput.value.trim() : '';
  var params = ['status=finalizado', 'page=' + pageFinalizados, 'per_page=' + PER_PAGE, 'order_by=' + encodeURIComponent(orderByFinalizados), 'sort=' + encodeURIComponent(sortDirFinalizados)];
  if (filtroLojaFinalizados) params.push('loja=' + encodeURIComponent(filtroLojaFinalizados));
  if (termoBusca) params.push('busca=' + encodeURIComponent(termoBusca));
  params.push('_=' + (Date.now ? Date.now() : new Date().getTime())); // evita cache do GET
  var url = '/api/pedidos?' + params.join('&');

  api(url)
    .then(function (r) { return r.json(); })
    .then(function (data) {
      var lista = data.pedidos || [];
      var total = data.total != null ? data.total : lista.length;
      var totalPages = data.total_pages != null ? data.total_pages : 1;

      if (!lista || !lista.length) {
        container.innerHTML = '<p>Nenhum pedido finalizado' + (termoBusca ? ' para "' + termoBusca + '"' : '') + '.</p>';
        document.getElementById('paginacao-finalizados').innerHTML = '';
        return;
      }

      var indicadorLoja = filtroLojaFinalizados ? ' (Filtrado: ' + filtroLojaFinalizados + ')' : '';
      var isAdmin = usuario && usuario.categoria === 'ADMIN';
      function thOrdenavel(col, label) {
        var ativo = orderByFinalizados === col;
        var seta = ativo ? (sortDirFinalizados === 'asc' ? ' ▲' : ' ▼') : '';
        return '<th class="coluna-ordenavel" onclick="ordenarFinalizados(\'' + col + '\')" title="Ordenar">' + label + seta + '</th>';
      }
      var html = '<table><thead><tr>';
      html += thOrdenavel('numero_pedido', 'Nº Pedido');
      html += '<th class="coluna-filtravel" onclick="mostrarFiltroLojaFinalizados(event)">Loja' + indicadorLoja + ' ▼</th>';
      html += thOrdenavel('marketplace', 'Marketplace');
      html += thOrdenavel('frete_cliente', 'Frete (R$)');
      html += thOrdenavel('peso', 'Peso (kg)');
      html += thOrdenavel('transportadora', 'Transportadora');
      html += '<th>Frete real (R$)</th>';
      html += '<th>Embalagem</th>';
      html += thOrdenavel('tracking_code', 'Rastreio');
      html += thOrdenavel('data_finalizacao', 'Data finalização');
      html += '<th>Ações</th></tr></thead><tbody>';
      lista.forEach(function (p) {
        var num = (p.numero_pedido || '').replace(/'/g, "\\'");
        var freteReal = p.custo_mandae != null ? Number(p.custo_mandae).toFixed(2) : '-';
        var peso = p.peso != null ? Number(p.peso).toFixed(2) : '-';
        var embalagemNome = '-';
        if (p.embalagens && p.embalagens.length > 0) {
          embalagemNome = p.embalagens.map(function(emb) {
            var nome = (emb.embalagem && emb.embalagem.nome) ? emb.embalagem.nome : 'Desconhecida';
            var qtd = emb.quantidade || 1;
            return nome + ' (x' + qtd + ')';
          }).join(', ');
        } else if (p.embalagem && p.embalagem.nome) {
          embalagemNome = p.embalagem.nome + ' (x' + (p.quantidade_embalagem || 1) + ')';
        }
        var dataFinalizacao = p.data_finalizacao || '-';
        if (dataFinalizacao !== '-' && dataFinalizacao) {
          try { dataFinalizacao = new Date(dataFinalizacao).toLocaleDateString('pt-BR'); } catch (e) {}
        }
        html += '<tr><td>' + (p.numero_pedido || '-') + '</td><td>' + (p.loja_nome || '-') + '</td><td>' + (p.marketplace || '-') +
          '</td><td>' + (p.frete_cliente != null ? Number(p.frete_cliente).toFixed(2) : '-') + '</td><td>' + peso +
          '</td><td>' + (p.transportadora || '-') + '</td><td>' + freteReal +
          '</td><td>' + embalagemNome + '</td><td>' + (p.tracking_code || '-') + '</td><td>' + dataFinalizacao + '</td><td>';
        html += '<button type="button" class="btn-acao" onclick="abrirModalEditarFinalizado(\'' + num + '\')">Editar</button>';
        if (isAdmin) {
          html += ' <button type="button" class="btn-acao btn-excluir" onclick="excluirPedido(\'' + num + '\')" title="Excluir (só admin)">Excluir</button>';
        }
        html += '</td></tr>';
      });
      html += '</tbody></table>';
      container.innerHTML = html;
      renderizarPaginacaoFinalizados(pageFinalizados, totalPages, total);
    })
    .catch(function () {
      container.innerHTML = '<p class="erro">Erro ao carregar finalizados.</p>';
      document.getElementById('paginacao-finalizados').innerHTML = '';
    });
}

function renderizarPaginacaoFinalizados(paginaAtual, totalPaginas, total) {
  var el = document.getElementById('paginacao-finalizados');
  if (!el) return;
  if (totalPaginas <= 1 && total <= PER_PAGE) {
    el.innerHTML = '';
    return;
  }
  var html = '<div class="paginacao"><span>Página ' + paginaAtual + ' de ' + totalPaginas + '</span> ';
  if (paginaAtual > 1) html += '<button type="button" class="btn-secundario" onclick="carregarFinalizados(' + (paginaAtual - 1) + ')">Anterior</button> ';
  if (paginaAtual < totalPaginas) html += '<button type="button" class="btn-secundario" onclick="carregarFinalizados(' + (paginaAtual + 1) + ')">Próxima</button>';
  html += '</div>';
  el.innerHTML = html;
}

function mostrarFiltroLojaFinalizados(event) {
  event.stopPropagation();
  var dropdownExistente = document.getElementById('dropdown-filtro-loja-finalizados');
  if (dropdownExistente) { dropdownExistente.remove(); return; }
  var dropdown = document.createElement('div');
  dropdown.id = 'dropdown-filtro-loja-finalizados';
  dropdown.className = 'dropdown-filtro-loja';
  var opcaoTodas = document.createElement('div');
  opcaoTodas.className = 'dropdown-item' + (!filtroLojaFinalizados ? ' ativo' : '');
  opcaoTodas.textContent = 'Todas';
  opcaoTodas.onclick = function(e) { e.stopPropagation(); filtroLojaFinalizados = null; carregarFinalizados(); dropdown.remove(); };
  dropdown.appendChild(opcaoTodas);
  LOJAS_DISPONIVEIS.forEach(function(loja) {
    var opcao = document.createElement('div');
    opcao.className = 'dropdown-item' + (filtroLojaFinalizados === loja ? ' ativo' : '');
    opcao.textContent = loja;
    opcao.onclick = function(e) { e.stopPropagation(); filtroLojaFinalizados = loja; carregarFinalizados(); dropdown.remove(); };
    dropdown.appendChild(opcao);
  });
  var th = event.currentTarget;
  var rect = th.getBoundingClientRect();
  dropdown.style.position = 'fixed';
  dropdown.style.top = (rect.bottom + window.scrollY) + 'px';
  dropdown.style.left = rect.left + 'px';
  dropdown.style.minWidth = rect.width + 'px';
  document.body.appendChild(dropdown);
  setTimeout(function() {
    document.addEventListener('click', function fechar() { dropdown.remove(); document.removeEventListener('click', fechar); }, { once: true });
  }, 0);
}

function obterRastreioEmLote() {
  var btn = document.getElementById('btn-obter-rastreio-lote');
  var btnText = btn ? btn.textContent : '';
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Processando... (aguarde, pode levar vários minutos)';
  }
  var avisoFinalizados = document.getElementById('planilha-mandae-aviso');
  if (avisoFinalizados) {
    avisoFinalizados.textContent = 'Obtendo rastreios em lote... O sistema está processando cada pedido com intervalo de 5 segundos. Aguarde.';
    avisoFinalizados.classList.remove('oculto');
    avisoFinalizados.style.color = '#0066cc';
  }
  api('/api/pedidos/obter-rastreio-em-lote', { method: 'POST' })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      if (btn) { btn.disabled = false; btn.textContent = btnText; }
      if (avisoFinalizados) { avisoFinalizados.classList.add('oculto'); avisoFinalizados.textContent = ''; }
      alert('Rastreio em lote: ' + (d.atualizados || 0) + ' pedido(s) atualizado(s).' + (d.erros && d.erros.length ? ' ' + d.erros.length + ' erro(s).' : ''));
      carregarFinalizados();
    })
    .catch(function () {
      if (btn) { btn.disabled = false; btn.textContent = btnText; }
      if (avisoFinalizados) { avisoFinalizados.classList.add('oculto'); avisoFinalizados.textContent = ''; }
      alert('Erro ao obter rastreio em lote.');
    });
}

function exportarFinalizadosExcel() {
  var params = [];
  if (filtroLojaFinalizados) params.push('loja=' + encodeURIComponent(filtroLojaFinalizados));
  var buscaInput = document.getElementById('busca-finalizados');
  var termoBusca = buscaInput ? buscaInput.value.trim() : '';
  if (termoBusca) params.push('busca=' + encodeURIComponent(termoBusca));
  var url = '/api/pedidos/exportar-finalizados' + (params.length ? '?' + params.join('&') : '');
  api(url)
    .then(function (r) {
      if (!r.ok) return r.json().then(function (err) { throw new Error(err.erro || 'Erro ao exportar'); });
      return r.blob();
    })
    .then(function (blob) {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'finalizados-' + new Date().toISOString().slice(0, 10) + '.xlsx';
      a.click();
      URL.revokeObjectURL(a.href);
    })
    .catch(function (e) {
      alert(e.message || 'Erro ao exportar para Excel.');
    });
}

function confirmarFinalizar() {
  if (!pedidoEmFinalizacao) return;
  var avisoEl = document.getElementById('modal-finalizar-aviso');
  avisoEl.classList.add('oculto');

  // Obrigatoriedade global: impedir finalizar sem ter clicado em "Obter informações do pedido" (vale para todos os usuários)
  if (!blingInfoObtida) {
    avisoEl.textContent = 'É obrigatório clicar em "Obter informações do pedido" antes de finalizar.';
    avisoEl.classList.remove('oculto');
    avisoEl.style.color = '#cc0000';
    return;
  }

  // Coletar todas as embalagens do formulário
  var embalagens = coletarEmbalagensDoForm();
  if (embalagens.length === 0) {
    avisoEl.textContent = 'Adicione pelo menos uma embalagem.';
    avisoEl.classList.remove('oculto');
    return;
  }

  var mktInput = document.getElementById('modal-finalizar-marketplace');
  var marketplace = (mktInput && mktInput.value.trim()) ? mktInput.value.trim() : 'site';
  var frete = parseFloat(document.getElementById('modal-finalizar-frete').value) || 0;
  var transpInput = document.getElementById('modal-finalizar-transportadora');
  var transportadora = (transpInput && transpInput.value.trim()) ? transpInput.value.trim() : null;
  if (transportadora === '') transportadora = null;
  var tracking = document.getElementById('modal-finalizar-tracking').value.trim() || null;
  var observacoes = document.getElementById('modal-observacoes').value;
  var custoMandaeEl = document.getElementById('modal-finalizar-custo-mandae');
  var custoMandaeVal = custoMandaeEl ? custoMandaeEl.value.trim() : '';
  var custoMandae = custoMandaeVal !== '' ? parseFloat(custoMandaeVal.replace(',', '.')) : null;

  var payloadFinalizar = {
    embalagens: embalagens,  // Array de {embalagem_id, quantidade}
    observacoes: observacoes,
  };
  
  // Manter compatibilidade: se tiver apenas 1 embalagem, também enviar campos antigos
  if (embalagens.length === 1) {
    payloadFinalizar.id_embalagem = embalagens[0].embalagem_id;
    payloadFinalizar.quantidade_embalagem = embalagens[0].quantidade;
  }
  if (custoMandae != null && !isNaN(custoMandae) && custoMandae >= 0) {
    payloadFinalizar.custo_mandae = custoMandae;
  }

  var numero = pedidoEmFinalizacao;
  var pesoInput = document.getElementById('modal-finalizar-peso');
  var peso = pesoInput && pesoInput.value.trim() !== '' ? parseFloat(pesoInput.value) : null;

  api('/api/pedidos/' + encodeURIComponent(numero), {
    method: 'PUT',
    body: JSON.stringify({
      marketplace: marketplace,
      frete_cliente: frete,
      peso: peso,
      transportadora: transportadora,
      tracking_code: tracking
    })
  })
    .then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.erro || 'Erro ao salvar dados do pedido.');
        return d;
      });
    })
    .then(function () {
      return api('/api/pedidos/' + encodeURIComponent(numero) + '/finalizar', {
        method: 'POST',
        body: JSON.stringify(payloadFinalizar),
      });
    })
    .then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.erro || 'Erro ao finalizar.');
        return d;
      });
    })
    .then(function () {
      // A reserva já é removida automaticamente no backend ao finalizar
      pedidoReservado = false;
      fecharModal();
      alert('Pedido finalizado com sucesso. Ele saiu da lista em aberto e aparece em Finalizados.');
      carregarPedidos();
      carregarFinalizados(1); // Força página 1 para exibir o pedido recém-finalizado no topo
      carregarDashboard();
    })
    .catch(function (e) {
      avisoEl.textContent = e.message || 'Erro ao finalizar.';
      avisoEl.classList.remove('oculto');
    });
}

// Embalagens no modal de edição (lista disponível ao abrir)
var embalagensDisponiveisEditar = [];

function adicionarEmbalagemItemEditar(embalagemIdSelecionada, quantidade) {
  var container = document.getElementById('modal-editar-embalagens-container');
  if (!container) return;
  var index = container.children.length;
  var itemDiv = document.createElement('div');
  itemDiv.className = 'embalagem-item';
  itemDiv.style.marginBottom = '0.5rem';
  itemDiv.style.display = 'flex';
  itemDiv.style.alignItems = 'center';
  var select = document.createElement('select');
  select.className = 'select-embalagem-item-editar';
  select.setAttribute('data-index', index);
  select.innerHTML = '<option value="">Selecione uma embalagem</option>';
  (embalagensDisponiveisEditar || []).forEach(function(e) {
    var option = document.createElement('option');
    option.value = e.id;
    option.textContent = (e.nome || '') + ' (R$ ' + (e.custo != null ? Number(e.custo).toFixed(2) : '') + ')';
    if (embalagemIdSelecionada && e.id == embalagemIdSelecionada) option.selected = true;
    select.appendChild(option);
  });
  var qtdInput = document.createElement('input');
  qtdInput.type = 'number';
  qtdInput.className = 'quantidade-embalagem-item-editar';
  qtdInput.setAttribute('data-index', index);
  qtdInput.min = 1;
  qtdInput.value = quantidade || 1;
  qtdInput.step = 1;
  qtdInput.placeholder = 'Qtd';
  qtdInput.style.width = '80px';
  qtdInput.style.marginLeft = '0.5rem';
  var btnRemover = document.createElement('button');
  btnRemover.type = 'button';
  btnRemover.className = 'btn-remover-embalagem-editar';
  btnRemover.setAttribute('data-index', index);
  btnRemover.textContent = '✕';
  btnRemover.onclick = function() { removerEmbalagemItemEditar(index); };
  btnRemover.style.marginLeft = '0.5rem';
  btnRemover.style.display = index === 0 ? 'none' : 'inline-block';
  itemDiv.appendChild(select);
  itemDiv.appendChild(qtdInput);
  itemDiv.appendChild(btnRemover);
  container.appendChild(itemDiv);
  atualizarVisibilidadeBotoesRemoverEditar();
}

function removerEmbalagemItemEditar(index) {
  var container = document.getElementById('modal-editar-embalagens-container');
  if (!container || container.children.length <= 1) return;
  var item = container.children[index];
  if (item) {
    container.removeChild(item);
    atualizarIndicesEmbalagensEditar();
  }
}

function atualizarIndicesEmbalagensEditar() {
  var container = document.getElementById('modal-editar-embalagens-container');
  if (!container) return;
  Array.from(container.children).forEach(function(item, index) {
    var select = item.querySelector('.select-embalagem-item-editar');
    var qtdInput = item.querySelector('.quantidade-embalagem-item-editar');
    var btnRemover = item.querySelector('.btn-remover-embalagem-editar');
    if (select) select.setAttribute('data-index', index);
    if (qtdInput) qtdInput.setAttribute('data-index', index);
    if (btnRemover) {
      btnRemover.setAttribute('data-index', index);
      btnRemover.onclick = function() { removerEmbalagemItemEditar(index); };
    }
  });
  atualizarVisibilidadeBotoesRemoverEditar();
}

function atualizarVisibilidadeBotoesRemoverEditar() {
  var container = document.getElementById('modal-editar-embalagens-container');
  if (!container) return;
  Array.from(container.children).forEach(function(item, index) {
    var btnRemover = item.querySelector('.btn-remover-embalagem-editar');
    if (btnRemover) btnRemover.style.display = container.children.length > 1 ? 'inline-block' : 'none';
  });
}

function coletarEmbalagensDoFormEditar() {
  var container = document.getElementById('modal-editar-embalagens-container');
  if (!container) return [];
  var embalagens = [];
  Array.from(container.children).forEach(function(item) {
    var select = item.querySelector('.select-embalagem-item-editar');
    var qtdInput = item.querySelector('.quantidade-embalagem-item-editar');
    if (select && select.value && qtdInput) {
      var id = parseInt(select.value, 10);
      var qtd = parseInt(qtdInput.value, 10) || 1;
      if (id && qtd >= 1) embalagens.push({ embalagem_id: id, quantidade: qtd });
    }
  });
  return embalagens;
}

// Modal editar pedido finalizado (rastreio, custo Mandaê e embalagens)
function abrirModalEditarFinalizado(numeroPedido) {
  var numEl = document.getElementById('modal-editar-finalizado-num');
  var numInput = document.getElementById('modal-editar-finalizado-numero');
  var avisoEl = document.getElementById('modal-editar-finalizado-aviso');
  numEl.textContent = numeroPedido;
  if (numInput) numInput.value = numeroPedido;
  document.getElementById('modal-editar-marketplace').value = '';
  document.getElementById('modal-editar-frete').value = '';
  document.getElementById('modal-editar-peso').value = '';
  document.getElementById('modal-editar-transportadora').value = '';
  document.getElementById('modal-editar-tracking').value = '';
  document.getElementById('modal-editar-custo-mandae').value = '';
  avisoEl.classList.add('oculto');
  document.getElementById('modal-editar-finalizado').classList.remove('oculto');

  var containerEmb = document.getElementById('modal-editar-embalagens-container');
  containerEmb.innerHTML = '';

  Promise.all([
    api('/api/pedidos/' + encodeURIComponent(numeroPedido) + '/detalhes').then(function(r) { return r.json(); }),
    api('/api/embalagens').then(function(r) { return r.json(); })
  ])
    .then(function(results) {
      var d = results[0];
      var embList = Array.isArray(results[1]) ? results[1] : [];
      var excluirNomesEditar = ['Caixa G', 'Caixa M', 'Caixa P', 'Envelope'];
      embalagensDisponiveisEditar = embList.filter(function(e) {
        var nome = (e.nome || '').trim();
        return excluirNomesEditar.indexOf(nome) === -1;
      });

      document.getElementById('modal-editar-marketplace').value = d.marketplace || '';
      document.getElementById('modal-editar-frete').value = d.frete_cliente != null ? Number(d.frete_cliente) : '';
      document.getElementById('modal-editar-peso').value = d.peso != null ? Number(d.peso) : '';
      document.getElementById('modal-editar-transportadora').value = d.transportadora || '';
      document.getElementById('modal-editar-tracking').value = d.tracking_code || '';
      if (d.custo_mandae != null && d.custo_mandae !== '') {
        document.getElementById('modal-editar-custo-mandae').value = Number(d.custo_mandae);
      }

      if (d.embalagens && d.embalagens.length > 0) {
        d.embalagens.forEach(function(emb) {
          var embId = emb.embalagem_id || (emb.embalagem && emb.embalagem.id);
          var qtd = emb.quantidade || 1;
          adicionarEmbalagemItemEditar(embId, qtd);
        });
      } else if (d.id_embalagem || (d.embalagem && d.embalagem.id)) {
        var idEmb = d.id_embalagem || (d.embalagem && d.embalagem.id);
        var qtdEmb = d.quantidade_embalagem || 1;
        adicionarEmbalagemItemEditar(idEmb, qtdEmb);
      } else {
        adicionarEmbalagemItemEditar(null, 1);
      }
    })
    .catch(function () {
      adicionarEmbalagemItemEditar(null, 1);
    });
}

function sincronizarRastreioFinalizado() {
  var numInput = document.getElementById('modal-editar-finalizado-numero');
  var numero = numInput ? numInput.value.trim() : '';
  if (!numero) return;
  
  var avisoEl = document.getElementById('modal-editar-finalizado-aviso');
  avisoEl.textContent = 'Sincronizando código de rastreio...';
  avisoEl.classList.remove('oculto');
  avisoEl.style.color = '#0066cc';
  
  api('/api/pedidos/' + encodeURIComponent(numero) + '/sincronizar-rastreio', {
    method: 'POST'
  })
    .then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.erro || 'Erro ao sincronizar rastreio.');
        return d;
      });
    })
    .then(function (d) {
      if (d.tracking_code) {
        document.getElementById('modal-editar-tracking').value = d.tracking_code;
        avisoEl.textContent = 'Código de rastreio atualizado com sucesso!';
        avisoEl.style.color = '#006600';
      } else {
        avisoEl.textContent = 'Código de rastreio não encontrado no Bling.';
        avisoEl.style.color = '#666';
      }
    })
    .catch(function (e) {
      avisoEl.textContent = e.message || 'Erro ao sincronizar rastreio.';
      avisoEl.style.color = '#cc0000';
    });
}

function fecharModalEditarFinalizado() {
  document.getElementById('modal-editar-finalizado').classList.add('oculto');
  carregarFinalizados();
}

function salvarEditarFinalizado() {
  var numInput = document.getElementById('modal-editar-finalizado-numero');
  var numero = numInput ? numInput.value.trim() : '';
  if (!numero) return;
  var avisoEl = document.getElementById('modal-editar-finalizado-aviso');
  avisoEl.classList.add('oculto');

  var embalagens = coletarEmbalagensDoFormEditar();
  if (embalagens.length === 0) {
    avisoEl.textContent = 'Adicione pelo menos uma embalagem.';
    avisoEl.classList.remove('oculto');
    return;
  }

  var marketplace = document.getElementById('modal-editar-marketplace').value.trim() || null;
  var frete = document.getElementById('modal-editar-frete').value.trim();
  var freteVal = frete !== '' ? parseFloat(frete) : null;
  var peso = document.getElementById('modal-editar-peso').value.trim();
  var pesoVal = peso !== '' ? parseFloat(peso) : null;
  var transportadora = document.getElementById('modal-editar-transportadora').value.trim() || null;
  var tracking = document.getElementById('modal-editar-tracking').value.trim() || null;
  var custoEl = document.getElementById('modal-editar-custo-mandae');
  var custoMandae = custoEl && custoEl.value.trim() !== '' ? parseFloat(custoEl.value) : null;
  
  var payload = { embalagens: embalagens };
  if (marketplace !== null) payload.marketplace = marketplace;
  if (freteVal !== null) payload.frete_cliente = freteVal;
  if (pesoVal !== null) payload.peso = pesoVal;
  if (transportadora !== null) payload.transportadora = transportadora;
  if (tracking !== null) payload.tracking_code = tracking;
  if (custoMandae != null && !isNaN(custoMandae)) payload.custo_mandae = custoMandae;

  api('/api/pedidos/' + encodeURIComponent(numero) + '/editar-finalizado', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
    .then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.erro || 'Erro ao salvar.');
        return d;
      });
    })
    .then(function () {
      fecharModalEditarFinalizado();
      alert('Pedido finalizado atualizado.');
    })
    .catch(function (e) {
      avisoEl.textContent = e.message || 'Erro ao salvar.';
      avisoEl.classList.remove('oculto');
    });
}

// Embalagens
let embalagemEditandoId = null;

function carregarEmbalagens() {
  const container = document.getElementById('embalagens-lista');
  container.innerHTML = '<p>Carregando...</p>';

  api('/api/embalagens?status=ativo')
    .then(function (r) {
      return r.json();
    })
    .then(function (lista) {
      if (!lista || !lista.length) {
        container.innerHTML = '<p>Nenhuma embalagem cadastrada. Clique em "Nova embalagem" para criar.</p>';
        return;
      }
      let html =
        '<table><thead><tr><th>Nome</th><th>Custo (R$)</th><th>Estoque</th><th>Dimensões (cm)</th><th>Peso (kg)</th><th>Status</th><th>Ações</th></tr></thead><tbody>';
      lista.forEach(function (e) {
        html +=
          '<tr><td>' +
          (e.nome || '-') +
          '</td><td>' +
          (e.custo != null ? Number(e.custo).toFixed(2) : '-') +
          '</td><td>' +
          (e.estoque != null ? Number(e.estoque) : '0') +
          '</td><td>' +
          (e.altura != null && e.largura != null && e.comprimento != null
            ? e.altura + ' x ' + e.largura + ' x ' + e.comprimento
            : '-') +
          '</td><td>' +
          (e.peso != null ? Number(e.peso).toFixed(2) : '-') +
          '</td><td>' +
          (e.status || '-') +
          '</td><td class="celula-acoes"><button type="button" class="btn-acao btn-editar" onclick="abrirModalEmbalagem(' +
          e.id +
          ')">Editar</button> <button type="button" class="btn-acao btn-excluir" data-nome="' +
          (e.nome || '').replace(/"/g, '&quot;') +
          '" onclick="excluirEmbalagem(' +
          e.id +
          ', this)">Excluir</button></td></tr>';
      });
      html += '</tbody></table>';
      container.innerHTML = html;
    })
    .catch(function () {
      container.innerHTML = '<p class="erro">Erro ao carregar embalagens.</p>';
    });
}

function abrirModalEmbalagem(id) {
  embalagemEditandoId = id || null;
  document.getElementById('embalagem-id').value = id || '';
  document.getElementById('modal-embalagem-titulo').textContent = id ? 'Editar embalagem' : 'Nova embalagem';
  document.getElementById('embalagem-nome').value = '';
  document.getElementById('embalagem-custo').value = '';
  document.getElementById('embalagem-altura').value = '';
  document.getElementById('embalagem-largura').value = '';
  document.getElementById('embalagem-comprimento').value = '';
  document.getElementById('embalagem-peso').value = '';
  document.getElementById('embalagem-estoque').value = '0';

  if (id) {
    api('/api/embalagens/' + id)
      .then(function (r) {
        return r.json();
      })
      .then(function (e) {
        document.getElementById('embalagem-nome').value = e.nome || '';
        document.getElementById('embalagem-custo').value = e.custo != null ? e.custo : '';
        document.getElementById('embalagem-altura').value = e.altura != null ? e.altura : '';
        document.getElementById('embalagem-largura').value = e.largura != null ? e.largura : '';
        document.getElementById('embalagem-comprimento').value = e.comprimento != null ? e.comprimento : '';
        document.getElementById('embalagem-peso').value = e.peso != null ? e.peso : '';
        document.getElementById('embalagem-estoque').value = e.estoque != null ? e.estoque : '0';
      })
      .catch(function () {
        alert('Erro ao carregar embalagem.');
        return;
      });
  }
  document.getElementById('modal-embalagem').classList.remove('oculto');
}

function fecharModalEmbalagem() {
  document.getElementById('modal-embalagem').classList.add('oculto');
  embalagemEditandoId = null;
}

function salvarEmbalagem() {
  const nome = document.getElementById('embalagem-nome').value.trim();
  if (!nome) {
    alert('Nome é obrigatório.');
    return;
  }
  const custo = parseFloat(document.getElementById('embalagem-custo').value) || 0;
  const altura = parseFloat(document.getElementById('embalagem-altura').value) || 0;
  const largura = parseFloat(document.getElementById('embalagem-largura').value) || 0;
  const comprimento = parseFloat(document.getElementById('embalagem-comprimento').value) || 0;
  const pesoVal = document.getElementById('embalagem-peso').value.trim();
  const peso = pesoVal === '' ? null : parseFloat(pesoVal);
  const estoqueVal = document.getElementById('embalagem-estoque').value.trim();
  const estoque = estoqueVal === '' ? 0 : parseInt(estoqueVal, 10);
  if (isNaN(estoque) || estoque < 0) {
    alert('Estoque deve ser um número inteiro >= 0.');
    return;
  }

  if (embalagemEditandoId) {
    api('/api/embalagens/' + embalagemEditandoId, {
      method: 'PUT',
      body: JSON.stringify({
        nome: nome,
        custo: custo,
        altura: altura,
        largura: largura,
        comprimento: comprimento,
        peso: peso,
        estoque: estoque,
      }),
    })
      .then(function (r) {
        return r.json().then(function (d) {
          if (!r.ok) throw new Error(d.erro || 'Erro ao atualizar.');
          return d;
        });
      })
      .then(function () {
        fecharModalEmbalagem();
        alert('Embalagem atualizada com sucesso.');
        carregarEmbalagens();
      })
      .catch(function (e) {
        alert(e.message || 'Erro ao atualizar.');
      });
  } else {
    api('/api/embalagens', {
      method: 'POST',
      body: JSON.stringify({
        nome: nome,
        custo: custo,
        altura: altura,
        largura: largura,
        comprimento: comprimento,
        peso: peso,
        estoque: estoque,
      }),
    })
      .then(function (r) {
        return r.json().then(function (d) {
          if (!r.ok) throw new Error(d.erro || 'Erro ao criar.');
          return d;
        });
      })
      .then(function () {
        fecharModalEmbalagem();
        alert('Embalagem criada com sucesso.');
        carregarEmbalagens();
      })
      .catch(function (e) {
        alert(e.message || 'Erro ao criar.');
      });
  }
}

function excluirEmbalagem(id, btn) {
  var nome = (btn && btn.getAttribute && btn.getAttribute('data-nome')) || ('ID ' + id);
  if (!confirm('Desativar a embalagem "' + nome + '"?\n\n(Ela não aparecerá mais na lista de embalagens ativas.)')) {
    return;
  }
  api('/api/embalagens/' + id, { method: 'DELETE' })
    .then(function (r) {
      return r.json().then(function (d) {
        if (!r.ok) throw new Error(d.erro || 'Erro ao excluir.');
        return d;
      });
    })
    .then(function () {
      alert('Embalagem desativada.');
      carregarEmbalagens();
    })
    .catch(function (e) {
      alert(e.message || 'Erro ao excluir.');
    });
}

// Relatórios
function alternarTipoRelatorio() {
  const tipo = document.querySelector('input[name="tipo-relatorio"]:checked').value;
  const diarioDiv = document.getElementById('relatorio-diario-opcoes');
  const periodoDiv = document.getElementById('relatorio-periodo-opcoes');
  const porCanalDiv = document.getElementById('relatorio-por-canal-opcoes');
  diarioDiv.style.display = tipo === 'diario' ? 'flex' : 'none';
  periodoDiv.style.display = tipo === 'periodo' ? 'flex' : 'none';
  if (porCanalDiv) porCanalDiv.style.display = tipo === 'por-canal' ? 'flex' : 'none';
  if (tipo === 'periodo' || tipo === 'por-canal') {
    const hoje = new Date();
    const inicio = new Date(hoje);
    inicio.setDate(hoje.getDate() - 29);
    var inicioStr = inicio.toISOString().slice(0, 10);
    var fimStr = hoje.toISOString().slice(0, 10);
    if (document.getElementById('relatorio-data-inicio')) {
      document.getElementById('relatorio-data-inicio').value = inicioStr;
      document.getElementById('relatorio-data-fim').value = fimStr;
    }
    if (porCanalDiv && document.getElementById('relatorio-por-canal-inicio')) {
      document.getElementById('relatorio-por-canal-inicio').value = inicioStr;
      document.getElementById('relatorio-por-canal-fim').value = fimStr;
    }
  }
}

function gerarRelatorioPorCanal() {
  var inicio = document.getElementById('relatorio-por-canal-inicio').value;
  var fim = document.getElementById('relatorio-por-canal-fim').value;
  if (!inicio || !fim) {
    alert('Selecione as datas de início e fim.');
    return;
  }
  var container = document.getElementById('relatorio-conteudo');
  container.innerHTML = '<p class="aviso">Carregando...</p>';
  api('/api/relatorios/por-canal?inicio=' + encodeURIComponent(inicio) + '&fim=' + encodeURIComponent(fim))
    .then(function (r) {
      if (!r.ok) return r.json().then(function (e) { throw new Error(e.erro || 'Erro'); });
      return r.json();
    })
    .then(function (data) {
      var html = '<h3>Relatório por canal (' + (data.inicio || '') + ' a ' + (data.fim || '') + ')</h3>';
      if (!data.canais || !data.canais.length) {
        html += '<p>Nenhum dado no período.</p>';
        container.innerHTML = html;
        return;
      }
      data.canais.forEach(function (c) {
        html += '<div class="relatorio-secao"><h4>' + (c.canal || 'Não identificado') + '</h4>';
        html += '<table class="tabela-resumo-canal"><thead><tr><th>Pedidos</th><th>Custo total (R$)</th><th>Pago cliente (R$)</th><th>Frete real (R$)</th><th>Ganho/Perda (R$)</th></tr></thead><tbody><tr>';
        html += '<td>' + (c.total_pedidos || 0) + '</td>';
        html += '<td>R$ ' + (c.custo_total || 0).toFixed(2) + '</td>';
        html += '<td>R$ ' + (c.frete_total || 0).toFixed(2) + '</td>';
        html += '<td>R$ ' + (c.frete_real_total || 0).toFixed(2) + '</td>';
        html += '<td class="' + ((c.ganho_perda_liquido || 0) >= 0 ? 'positivo' : 'negativo') + '">R$ ' + (c.ganho_perda_liquido || 0).toFixed(2) + '</td>';
        html += '</tr></tbody></table>';
        if (c.caixas && c.caixas.length > 0) {
          html += '<table><thead><tr><th>Caixa</th><th>Quantidade</th><th>Custo unit. (R$)</th><th>Valor total (R$)</th></tr></thead><tbody>';
          c.caixas.forEach(function (cx) {
            html += '<tr><td>' + (cx.nome || '-') + '</td><td>' + (cx.quantidade || 0) + '</td><td>R$ ' + (cx.custo_unitario || 0).toFixed(2) + '</td><td>R$ ' + (cx.valor_total || 0).toFixed(2) + '</td></tr>';
          });
          html += '</tbody></table>';
        }
        html += '</div>';
      });
      container.innerHTML = html;
    })
    .catch(function (e) {
      container.innerHTML = '<p class="erro">' + (e.message || 'Erro ao gerar relatório por canal.') + '</p>';
    });
}

function exportarRelatorioPorCanalExcel() {
  var inicio = document.getElementById('relatorio-por-canal-inicio').value;
  var fim = document.getElementById('relatorio-por-canal-fim').value;
  if (!inicio || !fim) {
    alert('Selecione as datas de início e fim.');
    return;
  }
  var url = '/api/relatorios/por-canal/excel?inicio=' + encodeURIComponent(inicio) + '&fim=' + encodeURIComponent(fim);
  api(url)
    .then(function (r) {
      if (!r.ok) return r.json().then(function (e) { throw new Error(e.erro || 'Erro ao exportar'); });
      return r.blob();
    })
    .then(function (blob) {
      var a = document.createElement('a');
      a.href = window.URL.createObjectURL(blob);
      a.download = 'relatorio-por-canal-' + inicio + '-' + fim + '.xlsx';
      a.click();
      window.URL.revokeObjectURL(a.href);
    })
    .catch(function (e) {
      alert(e.message || 'Erro ao exportar Excel.');
    });
}

function gerarRelatorio() {
  const data = document.getElementById('relatorio-data').value;
  if (!data) {
    alert('Selecione uma data.');
    return;
  }
  const container = document.getElementById('relatorio-conteudo');
  container.innerHTML = '<p class="aviso">Carregando...</p>';

  api('/api/relatorios/diario/' + data)
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var ganhoPerdaLiquido = (d.ganho_total || 0) - (d.perda_total || 0);
      var html = '<div class="relatorio-cards">' +
        '<div class="relatorio-card"><div class="relatorio-card-label">Total de Pedidos</div><div class="relatorio-card-valor">' + (d.total_pedidos || 0) + '</div></div>' +
        '<div class="relatorio-card"><div class="relatorio-card-label">Custo Total (R$)</div><div class="relatorio-card-valor">R$ ' + (d.custo_total || 0).toFixed(2) + '</div></div>' +
        '<div class="relatorio-card"><div class="relatorio-card-label">Pago Cliente (R$)</div><div class="relatorio-card-valor">R$ ' + (d.frete_total || 0).toFixed(2) + '</div></div>' +
        '<div class="relatorio-card"><div class="relatorio-card-label">Frete Real (R$)</div><div class="relatorio-card-valor">R$ ' + (d.frete_real_total || 0).toFixed(2) + '</div></div>' +
        '<div class="relatorio-card"><div class="relatorio-card-label">Ganho/Perda (R$)</div><div class="relatorio-card-valor ' + (ganhoPerdaLiquido >= 0 ? 'positivo' : 'negativo') + '">R$ ' + ganhoPerdaLiquido.toFixed(2) + '</div></div>' +
        '</div>';
      if (d.embalagens_utilizadas && d.embalagens_utilizadas.length > 0) {
        html += '<div class="relatorio-secao"><h3>Embalagens utilizadas no dia</h3><table><thead><tr><th>Embalagem</th><th>Quantidade</th><th>Custo Unitário (R$)</th><th>Valor Total (R$)</th></tr></thead><tbody>';
        var totalGeralEmb = 0;
        d.embalagens_utilizadas.forEach(function (eu) {
          var vt = eu.valor_total || (eu.quantidade * (eu.custo_unitario || 0));
          totalGeralEmb += vt;
          html += '<tr><td>' + (eu.nome || '-') + '</td><td>' + (eu.quantidade || 0) + '</td><td>R$ ' + (eu.custo_unitario || 0).toFixed(2) + '</td><td>R$ ' + vt.toFixed(2) + '</td></tr>';
        });
        html += '<tr style="font-weight: bold;"><td colspan="3">Total</td><td>R$ ' + totalGeralEmb.toFixed(2) + '</td></tr></tbody></table></div>';
      }
      if (d.pedidos && d.pedidos.length > 0) {
        html += '<div class="relatorio-secao"><h3>Pedidos do dia</h3><table><thead><tr><th>Nº Pedido</th><th>Pago Cliente (R$)</th><th>Custo Total (R$)</th><th>Ganho/Perda (R$)</th></tr></thead><tbody>';
        d.pedidos.forEach(function (p) {
          var gp = p.ganho_perda != null ? p.ganho_perda : 0;
          html += '<tr><td>' + (p.numero_pedido || '-') + '</td><td>R$ ' + (p.frete_cliente || 0).toFixed(2) + '</td><td>R$ ' + (p.custo_total || 0).toFixed(2) + '</td><td class="' + (gp >= 0 ? 'positivo' : 'negativo') + '">R$ ' + gp.toFixed(2) + '</td></tr>';
        });
        html += '</tbody></table></div>';
      }
      if (d.total_pedidos === 0 && (!d.embalagens_utilizadas || d.embalagens_utilizadas.length === 0)) {
        html += '<p class="aviso">Nenhum dado encontrado para esta data.</p>';
      }
      container.innerHTML = html;
    })
    .catch(function () {
      container.innerHTML = '<p class="erro">Erro ao gerar relatório.</p>';
    });
}

function gerarRelatorioPeriodo() {
  const inicio = document.getElementById('relatorio-data-inicio').value;
  const fim = document.getElementById('relatorio-data-fim').value;
  if (!inicio || !fim) {
    alert('Selecione as datas de início e fim.');
    return;
  }
  
  // Validar período (máximo 90 dias)
  const inicioDate = new Date(inicio);
  const fimDate = new Date(fim);
  const dias = Math.ceil((fimDate - inicioDate) / (1000 * 60 * 60 * 24)) + 1;
  if (dias > 90) {
    alert('O período máximo permitido é de 90 dias.');
    return;
  }
  if (dias < 1) {
    alert('A data fim deve ser maior ou igual à data início.');
    return;
  }
  
  const container = document.getElementById('relatorio-conteudo');
  container.innerHTML = 'Carregando...';

  api('/api/relatorios/periodo?inicio=' + inicio + '&fim=' + fim)
    .then(function (r) {
      if (!r.ok) {
        return r.json().then(function(err) {
          throw new Error(err.erro || 'Erro ao gerar relatório');
        });
      }
      return r.json();
    })
    .then(function (data) {
      var html = '<div class="relatorio-cards">' +
        '<div class="relatorio-card"><div class="relatorio-card-label">Período</div><div class="relatorio-card-valor">' + (data.dias || 0) + ' dias</div></div>' +
        '<div class="relatorio-card"><div class="relatorio-card-label">Total de Pedidos</div><div class="relatorio-card-valor">' + (data.total_pedidos || 0) + '</div></div>' +
        '<div class="relatorio-card"><div class="relatorio-card-label">Custo Total (R$)</div><div class="relatorio-card-valor">R$ ' + (data.custo_total || 0).toFixed(2) + '</div></div>' +
        '<div class="relatorio-card"><div class="relatorio-card-label">Pago Cliente (R$)</div><div class="relatorio-card-valor">R$ ' + (data.frete_total || 0).toFixed(2) + '</div></div>' +
        '<div class="relatorio-card"><div class="relatorio-card-label">Frete Real (R$)</div><div class="relatorio-card-valor">R$ ' + (data.frete_real_total || 0).toFixed(2) + '</div></div>' +
        '<div class="relatorio-card"><div class="relatorio-card-label">Ganho/Perda (R$)</div><div class="relatorio-card-valor ' + ((data.ganho_perda_liquido || 0) >= 0 ? 'positivo' : 'negativo') + '">R$ ' + (data.ganho_perda_liquido || 0).toFixed(2) + '</div></div>' +
        '</div>';
      if (data.embalagens_utilizadas && data.embalagens_utilizadas.length > 0) {
        html += '<div class="relatorio-secao"><h3>Embalagens utilizadas no período</h3><table><thead><tr><th>Embalagem</th><th>Quantidade</th><th>Custo Unitário (R$)</th><th>Valor Total (R$)</th></tr></thead><tbody>';
        var totalGeralEmb = 0;
        data.embalagens_utilizadas.forEach(function (eu) {
          var vt = eu.valor_total || (eu.quantidade * (eu.custo_unitario || 0));
          totalGeralEmb += vt;
          html += '<tr><td>' + (eu.nome || '-') + '</td><td>' + (eu.quantidade || 0) + '</td><td>R$ ' + (eu.custo_unitario || 0).toFixed(2) + '</td><td>R$ ' + vt.toFixed(2) + '</td></tr>';
        });
        html += '<tr style="font-weight: bold;"><td colspan="3">Total</td><td>R$ ' + totalGeralEmb.toFixed(2) + '</td></tr></tbody></table></div>';
      }
      if (data.por_dia && data.por_dia.length > 0) {
        html += '<div class="relatorio-secao"><h3>Detalhamento por dia</h3><table><thead><tr><th>Data</th><th>Pedidos</th><th>Custo Total (R$)</th><th>Pago Cliente (R$)</th><th>Frete Real (R$)</th><th>Ganho/Perda (R$)</th></tr></thead><tbody>';
        data.por_dia.forEach(function(dia) {
          html += '<tr><td>' + dia.data + '</td><td>' + (dia.total_pedidos || 0) + '</td><td>R$ ' + (dia.custo_total || 0).toFixed(2) + '</td><td>R$ ' + (dia.frete_total || 0).toFixed(2) + '</td><td>R$ ' + (dia.frete_real_total || 0).toFixed(2) + '</td><td class="' + ((dia.ganho_perda_liquido || 0) >= 0 ? 'positivo' : 'negativo') + '">R$ ' + (dia.ganho_perda_liquido || 0).toFixed(2) + '</td></tr>';
        });
        html += '</tbody></table></div>';
      }
      if (!data.total_pedidos && (!data.embalagens_utilizadas || data.embalagens_utilizadas.length === 0)) {
        html += '<p class="aviso">Nenhum dado encontrado para o período.</p>';
      }
      container.innerHTML = html;
    })
    .catch(function (err) {
      container.innerHTML = '<p class="erro">Erro ao gerar relatório: ' + (err.message || 'Erro desconhecido') + '</p>';
    });
}

function baixarExcel() {
  const data = document.getElementById('relatorio-data').value;
  if (!data) {
    alert('Selecione uma data.');
    return;
  }
  api('/api/relatorios/diario/' + data + '/excel')
    .then(function (r) {
      return r.blob();
    })
    .then(function (blob) {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'relatorio-logistica-' + data + '.xlsx';
      a.click();
      URL.revokeObjectURL(a.href);
    })
    .catch(function () {
      alert('Erro ao baixar Excel.');
    });
}

function baixarExcelPeriodo() {
  const inicio = document.getElementById('relatorio-data-inicio').value;
  const fim = document.getElementById('relatorio-data-fim').value;
  if (!inicio || !fim) {
    alert('Selecione as datas de início e fim.');
    return;
  }
  
  // Validar período (máximo 90 dias)
  const inicioDate = new Date(inicio);
  const fimDate = new Date(fim);
  const dias = Math.ceil((fimDate - inicioDate) / (1000 * 60 * 60 * 24)) + 1;
  if (dias > 90) {
    alert('O período máximo permitido é de 90 dias.');
    return;
  }
  if (dias < 1) {
    alert('A data fim deve ser maior ou igual à data início.');
    return;
  }
  
  api('/api/relatorios/periodo/excel?inicio=' + inicio + '&fim=' + fim)
    .then(function (r) {
      if (!r.ok) {
        return r.json().then(function(err) {
          throw new Error(err.erro || 'Erro ao baixar Excel');
        });
      }
      return r.blob();
    })
    .then(function (blob) {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'relatorio-logistica-' + inicio + '-' + fim + '.xlsx';
      a.click();
      URL.revokeObjectURL(a.href);
    })
    .catch(function (err) {
      alert('Erro ao baixar Excel: ' + (err.message || 'Erro desconhecido'));
    });
}

// Bling
function carregarBlingStatus() {
  const container = document.getElementById('bling-status');
  container.innerHTML = 'Carregando...';

  fetch(API_BASE + '/api/bling/status')
    .then(function (r) {
      return r.json();
    })
    .then(function (data) {
      container.className = 'status-box ' + (data.conectado ? 'conectado' : 'desconectado');
      container.innerHTML = data.conectado
        ? '<strong>Bling conectado.</strong> Token configurado e válido.'
        : '<strong>Bling não conectado.</strong> Clique no link abaixo para autorizar o app no Bling.';
    })
    .catch(function () {
      container.className = 'status-box desconectado';
      container.innerHTML = 'Não foi possível verificar o status.';
    });
}

function limparDados() {
  if (!confirm('Remover TODOS os pedidos e custos do banco?\n\nIsso permite sincronizar novamente com o Bling do zero. Usuários e embalagens são mantidos.')) {
    return;
  }
  api('/api/admin/limpar-dados', { method: 'POST' })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      alert(d.mensagem || 'Dados removidos.');
      carregarPedidos();
      carregarFinalizados();
      carregarDashboard();
      if (typeof irPara === 'function') irPara('dashboard');
    })
    .catch(function (e) {
      alert(e.message || 'Erro ao limpar dados.');
    });
}
