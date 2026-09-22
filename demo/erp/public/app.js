const $ = (s, root = document) => root.querySelector(s);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money = v => '¥' + (Number(v || 0) / 100).toLocaleString('zh-CN', {minimumFractionDigits:2,maximumFractionDigits:2});
const date = v => v ? new Date(v).toLocaleString('zh-CN', {hour12:false}) : '—';
const roles = {admin:'系统管理员',buyer:'采购专员',seller:'销售专员',warehouse:'仓库管理员',finance:'财务专员',viewer:'只读观察员'};
const statuses = {draft:'草稿',pending:'待审批',approved:'已审批',completed:'已完成',cancelled:'已取消'};
const paths = {dashboard:['运营概览','掌握业务全貌，让每一笔流转清晰可见。'],products:['商品管理','统一管理商品档案、标准售价与安全库存。'],partners:['往来单位','维护客户与供应商，连接业务上下游。'],purchase:['采购管理','从采购计划到入库，追踪每一笔采购。'],sale:['销售管理','从客户订单到交付，让销售流程有序推进。'],inventory:['库存管理','实时库存与安全预警，准确掌握每一件商品。'],movements:['库存流水','每一次出入库，都有迹可循。'],finance:['财务结算','管理应收应付，记录每一笔收付款。'],audit:['操作日志','追溯业务操作，了解数据变更。'],settings:['系统设置','角色信息与演示环境管理。']};
const icons = {dashboard:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',products:'m3 7 9-4 9 4v10l-9 4-9-4z M3 7l9 4 9-4 M12 11v10',partners:'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M17 4a4 4 0 0 1 0 8 M22 21v-2a4 4 0 0 0-3-4',purchase:'M3 3h2l3 12h10l3-9H6 M9 20h.01 M18 20h.01',sale:'M4 4h16v16H4z M8 8h8 M8 12h8 M8 16h4',inventory:'m3 9 9-6 9 6v12H3z M8 21V11h8v10 M8 15h8',movements:'M4 7h16 M16 3l4 4-4 4 M20 17H4 M8 13l-4 4 4 4',finance:'M3 6h18v14H3z M3 10h18 M15 15h3',audit:'M6 3h12v18H6z M9 7h6 M9 11h6 M9 15h4',settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v3 M12 19v3 M2 12h3 M19 12h3 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2',arrow:'M5 12h14 M14 7l5 5-5 5',plus:'M12 5v14 M5 12h14',download:'M12 3v12 M7 10l5 5 5-5 M4 17v4h16v-4',logout:'M9 3H4v18h5 M10 12h11 M17 8l4 4-4 4'};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="${icons[name] || icons.products}"/></svg>`;
const badge = status => `<span class="badge ${esc(status)}">${esc(statuses[status] || ({enabled:'启用',disabled:'停用'}[status]) || status)}</span>`;
const button = (label, action, attrs = '', cls = '') => `<button type="button" class="${cls}" data-action="${action}" data-testid="${action}" ${attrs}>${label}</button>`;
let user, demo = true, route = 'dashboard', page = 1, filters = {}, rows = [], lookups, orderLines = [], listEndpoint = '', requestId = 0;
const can = (...r) => user?.role === 'admin' || r.includes(user?.role);
async function api(path, options = {}) {
  const response = await fetch('/api' + path, {credentials:'same-origin',...options,headers:{'Content-Type':'application/json',...options.headers},body:options.body === undefined ? undefined : JSON.stringify(options.body)});
  const data = await response.json();
  if (!response.ok) { if (response.status===401 && path!=='/auth/login') { user=null; $('#modal').close(); login(); } throw new Error(data.error?.message || '请求失败'); }
  return data;
}
let toastTimer;
function toast(text) { $('#toast').textContent=text; clearTimeout(toastTimer); toastTimer=setTimeout(()=>$('#toast').textContent='',3500); }
function login() {
  $('#app').innerHTML=`<main class="login"><section class="login-art"><div class="brand"><img src="/favicon.svg" alt="">启航 ERP<small>QIHANG ENTERPRISE</small></div><div><div class="eyebrow">CONNECTED BUSINESS, CLEARER DECISIONS</div><h1>让业务有序流转，<br>让增长清晰可见。</h1><p>采购 · 销售 · 库存 · 财务<br>一个工作台，连接企业运营的每个环节。</p><div class="decor"><span>01 / 业务协同</span><span>02 / 库存追溯</span><span>03 / 财务闭环</span></div></div><p>启航 ERP / 本地练习环境 · v1.0</p></section><section class="login-panel"><div class="login-box"><div class="eyebrow">WELCOME BACK</div><h2>登录工作台</h2><p>欢迎回来，开启今天的业务管理。</p><form id="login-form" data-testid="login-form"><label>用户名<input name="username" autocomplete="username" required maxlength="40" placeholder="请输入用户名" data-testid="login-username"></label><label>密码<input name="password" type="password" autocomplete="current-password" required maxlength="128" placeholder="请输入密码" data-testid="login-password"></label><div class="error" role="alert" id="login-error"></div><button class="primary" data-testid="login-submit">登录工作台 →</button></form><div class="demo-accounts">演示账号：admin / buyer / seller / warehouse / finance / viewer<br>统一初始密码：<span class="mono">Erp123456!</span></div></div></section></main>`;
}
function shell() {
  const nav = keys => keys.filter(k=>k!=='audit'||can('viewer')).map(k=>`<a href="#/${k}" class="${route===k?'active':''}" data-testid="nav-${k}">${icon(k)}<span>${paths[k][0]}</span></a>`).join('');
  $('#app').innerHTML=`<div class="layout"><aside class="sidebar"><a class="brand" href="#/dashboard"><img src="/favicon.svg" alt=""><span>启航 ERP<small>QIHANG ENTERPRISE</small></span></a><div class="nav-label">WORKSPACE / 工作空间</div><nav class="nav">${nav(['dashboard'])}</nav><div class="nav-label">BUSINESS / 业务管理</div><nav class="nav">${nav(['purchase','sale','inventory','finance'])}</nav><div class="nav-label">RESOURCES / 基础资料</div><nav class="nav">${nav(['products','partners','movements','audit','settings'])}</nav><div class="side-bottom"><div class="env"><span class="dot"></span>本地工作空间<br><small>启航 ERP · v1.0.0</small></div></div></aside><div class="workspace"><header class="topbar"><div class="crumb">工作空间　/　<strong>${paths[route][0]}</strong></div><div class="user"><span class="muted">${new Date().toLocaleDateString('zh-CN',{month:'long',day:'numeric',weekday:'long'})}</span><span class="avatar">${esc(user.name[0])}</span><span>${esc(user.name)}<br><small class="muted">${roles[user.role]}</small></span>${button(icon('logout'),'logout','aria-label="退出登录"','ghost')}</div></header><main class="content" id="content"><div class="loading">正在加载业务数据…</div></main></div></div>`;
}
const heading = actions => `<div class="page-head"><div><div class="eyebrow">QIHANG / ${route.toUpperCase()}</div><h1>${paths[route][0]}</h1><p>${paths[route][1]}</p></div><div class="row">${actions||''}</div></div>`;
const footer = () => '<footer class="footer"><span>启航 ERP · 企业运营工作台</span><span>LOCAL WORKSPACE / V1.0</span></footer>';
function stat(label,value,sub,feature=false,i='finance') { return `<div class="stat ${feature?'feature':''}"><div class="stat-top">${label}${icon(i)}</div><div class="stat-value">${value}</div><div class="stat-foot">${sub}</div></div>`; }
const empty = () => `<div class="empty">${icon('products')}<div>暂无符合条件的数据</div></div>`;
function table(headers, cells, data = rows) { return data.length ? `<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${data.map(r=>`<tr data-testid="row-${r.id ?? r.product_id+'-'+r.warehouse_id}">${cells(r).map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : empty(); }
const orderCells = r => [`<a href="#" data-action="order-detail" data-id="${r.id}" data-testid="order-${r.id}" class="mono">${esc(r.number)}</a>`,esc(r.partner),esc(r.warehouse),money(r.total),badge(r.status),`<small>${date(r.created_at)}</small>`,button('查看','order-detail',`data-id="${r.id}"`,'small')];
async function dashboard() {
  const d=await api('/dashboard');
  const days=Array.from({length:7},(_,i)=>{const t=new Date();t.setUTCDate(t.getUTCDate()-6+i);return t.toISOString().slice(0,10);});
  const max=Math.max(1,...d.trend.flatMap(r=>[r.sales,r.purchases]));
  const bars=days.map((day,i)=>{const r=d.trend.find(x=>x.day===day)||{sales:0,purchases:0};return `<g><rect x="${i*70+13}" y="${136-r.sales/max*115}" width="17" height="${Math.max(1,r.sales/max*115)}" rx="3" fill="#27755c"><title>${day} 销售 ${money(r.sales)}</title></rect><rect x="${i*70+34}" y="${136-r.purchases/max*115}" width="17" height="${Math.max(1,r.purchases/max*115)}" rx="3" fill="#c6dccc"><title>${day} 采购 ${money(r.purchases)}</title></rect><text x="${i*70+32}" y="157" text-anchor="middle" fill="#97a299" font-size="10">${day.slice(5)}</text></g>`;}).join('');
  return heading(button('查看库存 '+icon('arrow'),'go-inventory','','row'))+`<div class="stats">${stat('累计销售额',money(d.sales),'已完成销售单据总额',true,'sale')}${stat('累计采购额',money(d.purchases),'已完成采购单据总额',false,'purchase')}${stat('待处理单据',d.pending+' <small>笔</small>','待审批与待出入库',false,'audit')}${stat('在售商品',d.products+' <small>种</small>','当前启用的商品档案',false,'products')}</div><div class="grid2"><section class="card"><div class="card-head"><div><h2>业务趋势</h2><p>近 7 天 · 按已完成单据的创建日期统计（UTC）</p></div><span class="badge enabled">近 7 天</span></div><div class="card-body"><svg viewBox="0 0 490 165" class="trend-chart" role="img" aria-label="近七天采购销售金额"><path d="M0 136H490 M0 78H490 M0 20H490" stroke="#edf1ee" stroke-dasharray="3 4"/>${bars}</svg><div class="legend"><i></i>销售金额 <i class="alt"></i>采购金额${!d.trend.length?'　完成出入库后，趋势将显示实际业务数据。':''}</div></div></section><section class="card"><div class="card-head"><div><h2>库存预警</h2><p>优先关注低于安全库存的商品</p></div><a href="#/inventory?low=1">查看全部 →</a></div><div class="card-body">${d.lowStock.slice(0,3).map(r=>`<div class="low-item"><div>${esc(r.name)}<small>${esc(r.warehouse)} · 安全库存 ${r.min_stock} ${esc(r.unit)}</small></div><div class="low-number">${r.quantity}<span>${esc(r.unit)}</span></div></div>`).join('')||'<p class="muted">所有商品库存充足</p>'}</div></section></div><section class="card"><div class="card-head"><h2>最近单据</h2><a href="#/sale">全部销售单据 →</a></div>${table(['单据编号','往来单位','仓库','单据金额','状态','创建时间','操作'],orderCells,d.recent)}</section><section class="card"><div class="card-head"><h2>快捷工作入口</h2><span class="muted">连接日常业务</span></div><div class="card-body quick-grid">${[['purchase','采购管理','采购申请、审批与入库'],['sale','销售管理','销售订单、交付与收款'],['inventory','库存管理','库存查询、预警与盘点']].map(([k,n,s])=>`<a class="quick" href="#/${k}">${icon(k)}<span>${n}<small>${s}</small></span></a>`).join('')}</div></section>`+footer();
}
const option = (value,label,selected) => `<option value="${esc(value)}" ${String(value)===String(selected)?'selected':''}>${esc(label)}</option>`;
function toolbar(extra = '') { return `<form class="toolbar" id="filter-form"><input name="q" aria-label="搜索关键词" data-testid="search-input" placeholder="搜索编码、名称或单据…" value="${esc(filters.q||'')}">${extra}<button data-testid="search-submit">查询</button>${button('重置','clear-filters','','ghost')}<span class="muted">按最新记录排序</span></form>`; }
function pager(d) { const pages=Math.max(1,Math.ceil(d.total/d.pageSize));return `<div class="pagination"><span>共 ${d.total} 条记录 · 每页 ${d.pageSize} 条</span><div class="row">${button('上一页','prev',page<=1?'disabled':'','small')}<span data-testid="page-indicator">${page} / ${pages}</span>${button('下一页','next',page>=pages?'disabled':'','small')}</div></div>`; }
const statusFilter = () => `<select name="status" aria-label="单据状态">${option('','全部状态',filters.status)}${Object.entries(statuses).map(([v,n])=>option(v,n,filters.status)).join('')}</select>`;
function endpoint() { if(['purchase','sale','finance'].includes(route)) return '/orders'; return '/'+route; }
function queryParams(p = page, size = 10) { return new URLSearchParams({...filters,...(['purchase','sale'].includes(route)?{type:route}:route==='finance'?{status:'completed'}:{}),page:p,pageSize:size}); }
async function listing() {
  listEndpoint=endpoint(); const d=await api(`${listEndpoint}?${queryParams()}`); rows=d.items;
  let heads,cells,extra='',actions=button(icon('download')+' 导出本页','export-page','','row');
  if (route==='products') {
    if(can('buyer','warehouse')) actions+=button('+ 新增商品','new-master','','primary');
    heads=['商品编码','商品名称','分类 / 单位','标准售价','安全库存','状态','操作'];
    cells=r=>[`<span class="mono">${esc(r.code)}</span>`,esc(r.name),`${esc(r.category)} / ${esc(r.unit)}`,money(r.price),r.min_stock,badge(r.active?'enabled':'disabled'),can('buyer','warehouse')?button('编辑','edit-master',`data-id="${r.id}"`,'small')+(can()?button('删除','delete-master',`data-id="${r.id}"`,'small danger'):''):'—'];
  } else if(route==='partners') {
    if(can('buyer','seller')) actions+=button('+ 新增单位','new-master','','primary');
    extra=`<select name="type" aria-label="单位类型">${option('','全部类型',filters.type)}${option('supplier','供应商',filters.type)}${option('customer','客户',filters.type)}</select>`;
    heads=['单位编码','单位名称','类型','联系人','联系电话','状态','操作'];
    cells=r=>[`<span class="mono">${esc(r.code)}</span>`,esc(r.name),r.type==='customer'?'客户':'供应商',esc(r.contact)||'—',esc(r.phone)||'—',badge(r.active?'enabled':'disabled'),can(r.type==='supplier'?'buyer':'seller')?button('编辑','edit-master',`data-id="${r.id}"`,'small')+(can()?button('删除','delete-master',`data-id="${r.id}"`,'small danger'):''):'—'];
  } else if(['purchase','sale','finance'].includes(route)) {
    if(route!=='finance'&&can(route==='purchase'?'buyer':'seller')) actions+=button('+ 新建'+(route==='purchase'?'采购单':'销售单'),'new-order','','primary');
    extra=route==='finance'?`<select name="type" aria-label="结算类型">${option('','全部结算',filters.type)}${option('sale','应收款',filters.type)}${option('purchase','应付款',filters.type)}</select>`:statusFilter();
    heads=route==='finance'?['单据编号','往来单位','类型','单据总额','已结算','待结算','操作']:['单据编号','往来单位','仓库','单据金额','状态','创建时间','操作'];
    cells=route==='finance'?r=>[`<a href="#" data-action="order-detail" data-id="${r.id}" class="mono">${esc(r.number)}</a>`,esc(r.partner),r.type==='sale'?'应收款':'应付款',money(r.total),money(r.paid),money(r.total-r.paid),button(can('finance')&&r.paid<r.total?'查看 / 结算':'查看','order-detail',`data-id="${r.id}"`,'small')]:orderCells;
  } else if(route==='inventory') {
    lookups=await api('/lookups');
    extra=`<select name="warehouse_id" aria-label="仓库">${option('','全部仓库',filters.warehouse_id)}${lookups.warehouses.map(w=>option(w.id,w.name,filters.warehouse_id)).join('')}</select><select name="low" aria-label="库存状态">${option('','全部库存',filters.low)}${option('1','仅库存预警',filters.low)}</select>`;
    heads=['商品编码','商品名称','仓库','当前库存','安全库存','库存状态','操作'];
    cells=r=>[esc(r.code),`${esc(r.name)}${!r.active?'<small>商品已停用</small>':''}`,esc(r.warehouse),`<strong>${r.quantity}</strong> ${esc(r.unit)}`,r.min_stock,r.quantity<r.min_stock&&r.active?'<span class="badge pending">库存偏低</span>':badge('enabled').replace('启用','正常'),can('warehouse')?button('盘点','adjust',`data-product="${r.product_id}" data-warehouse="${r.warehouse_id}"`,'small'):'—'];
  } else if(route==='movements') {
    heads=['流水编号','商品','仓库','变动数量','变动后库存','业务原因','关联单据','操作人 / 时间'];
    cells=r=>[r.id,`${esc(r.name)}<small>${esc(r.code)}</small>`,esc(r.warehouse),`<strong>${r.delta>0?'+':''}${r.delta}</strong>`,r.balance,esc(r.reason),r.order_id?`<a href="#" data-action="order-detail" data-id="${r.order_id}">${esc(r.order_number)}</a>`:'期初 / 盘点',`${esc(r.operator)}<small>${date(r.created_at)}</small>`];
  } else if(route==='audit') {
    heads=['日志编号','操作人','操作','对象','详情','时间']; cells=r=>[r.id,esc(r.operator),esc(({submit:'提交',approve:'审批通过',reject:'驳回',complete:'完成出入库',cancel:'取消',pay:'结算'})[r.action]||r.action),esc(r.entity),esc(r.detail)||'—',date(r.created_at)];
  }
  let summary=''; if(route==='finance'){const s=await api('/dashboard');summary=`<div class="stats finance-stats">${stat('待收款',money(s.receivable),'已完成销售单据的未收金额',true)}${stat('待付款',money(s.payable),'已完成采购单据的未付金额')}${stat('已完成销售额',money(s.sales),'累计完成的销售单据')}</div>`;}
  return heading(actions)+summary+`<section class="card">${toolbar(extra)}${table(heads,cells)}${pager(d)}</section>`+footer();
}
async function settings() {
  const users=can()?await api('/users'):[];
  const desc={admin:'维护所有资料、审批订单、出入库、结算及恢复演示数据。',buyer:'维护商品与供应商，创建、编辑、提交和取消采购单。',seller:'维护客户，创建、编辑、提交和取消销售单。',warehouse:'维护商品，执行已审批订单的出入库和库存盘点。',finance:'查看业务数据，为已完成单据登记收付款。',viewer:'只读查看业务与日志，不可修改任何业务数据。'};
  return heading('')+`<section class="card"><div class="card-head"><h2>角色与权限</h2><span class="badge enabled">6 个预设角色</span></div><div class="card-body role-grid">${Object.entries(roles).map(([r,n])=>`<div class="role-card"><span class="avatar">${n[0]}</span><h3>${n}</h3><p>${desc[r]}</p><span class="mono muted">${r}</span></div>`).join('')}</div></section>${users.length?`<section class="card"><div class="card-head"><h2>演示账号</h2><span class="muted">初始密码：Erp123456!</span></div>${table(['ID','用户名','姓名','角色'],r=>[r.id,esc(r.username),esc(r.name),roles[r.role]],users)}</section>`:''}${can()&&demo?`<section class="card"><div class="card-head"><h2>演示数据管理</h2></div><div class="card-body"><p class="muted">恢复后将清除所有当前业务数据，恢复初始商品、库存、单据和账号，并使所有会话失效。</p>${button('恢复演示数据','reset-dialog','','danger')}</div></section>`:''}`+footer();
}
async function render() {
  if(!user) return; const id=++requestId; shell();
  try {const html=route==='dashboard'?await dashboard():route==='settings'?await settings():await listing();if(id===requestId&&user) $('#content').innerHTML=html;}
  catch(e){if(id===requestId&&user) $('#content').innerHTML=heading('')+`<div class="error" role="alert">${esc(e.message)}</div>`;}
}
function navigate() { const [r,q]=(location.hash.replace(/^#\/?/,'')||'dashboard').split('?');route=paths[r]?r:'dashboard';page=1;filters=Object.fromEntries(new URLSearchParams(q));$('#modal').close();render(); }
function modal(title,html) {const d=$('#modal');d.innerHTML=`<div class="modal-head"><h2 id="modal-title">${title}</h2>${button('×','close-modal','aria-label="关闭弹窗"','ghost')}</div><div class="modal-body">${html}</div>`;if(!d.open)d.showModal();}
const modalFooter = label => `<div class="error" id="form-error" role="alert"></div><div class="modal-footer">${button('取消','close-modal')}<button class="primary" data-testid="form-submit">${label}</button></div>`;
const field = (label,name,value='',type='text',attrs='') => `<label>${label}<input name="${name}" data-testid="field-${name}" type="${type}" value="${esc(value)}" ${attrs}></label>`;
async function masterForm(id) {
  const isProduct=route==='products', r=id?await api(`/${route}/${id}`):{active:1,price:0,min_stock:10,type:user.role==='seller'?'customer':'supplier'};
  modal(`${id?'编辑':'新增'}${isProduct?'商品':'往来单位'}`,`<form id="master-form" data-id="${id||''}" data-version="${r.version||''}"><div class="form-grid">${field('编码 *','code',r.code,'text','required maxlength="30" pattern="[A-Za-z0-9_-]+"')}${field('名称 *','name',r.name,'text','required maxlength="100"')}${isProduct?`${field('分类 *','category',r.category,'text','required maxlength="30" list="categories"')}<datalist id="categories"><option>电脑设备</option><option>办公配件</option><option>办公家具</option><option>办公耗材</option><option>网络设备</option></datalist>${field('单位 *','unit',r.unit,'text','required maxlength="10"')}${field('标准售价（元） *','price',(r.price/100).toFixed(2),'number','required min="0" max="1000000" step="0.01"')}${field('安全库存 *','min_stock',r.min_stock,'number','required min="0" max="1000000" step="1"')}`:`<label>单位类型 *<select name="type" data-testid="field-type">${(can('buyer')?option('supplier','供应商',r.type):'')+(can('seller')?option('customer','客户',r.type):'')}</select></label>${field('联系人','contact',r.contact,'text','maxlength="50"')}${field('联系电话','phone',r.phone,'text','maxlength="30"')}`}<label>启用状态<select name="active" data-testid="field-active">${option(1,'启用',r.active)}${option(0,'停用',r.active)}</select></label></div>${modalFooter('保存')}</form>`);
}
function lineMarkup(i,n) { return `<div class="line-row" data-line="${n}"><select name="product_id" aria-label="第 ${n+1} 行商品" required><option value="">请选择商品</option>${lookups.products.filter(p=>p.active||p.id===i.product_id).map(p=>option(p.id,`${p.code} · ${p.name}${p.active?'':'（已停用）'}`,i.product_id)).join('')}</select><input name="quantity" aria-label="第 ${n+1} 行数量" type="number" value="${i.quantity}" min="1" max="10000" step="1" required><input name="price" aria-label="第 ${n+1} 行单价" type="number" value="${(i.price/100).toFixed(2)}" min="0" max="1000000" step="0.01" required><span class="line-total">${money(i.quantity*i.price)}</span>${button('×','remove-line',`data-index="${n}" aria-label="删除第 ${n+1} 行"`)}</div>`; }
function drawLines() { $('#order-lines').innerHTML=orderLines.map(lineMarkup).join(''); updateTotal(); }
function syncLines() {orderLines=Array.from(document.querySelectorAll('[data-line]')).map(el=>({product_id:Number($('[name=product_id]',el).value),quantity:Number($('[name=quantity]',el).value),price:Math.round(Number($('[name=price]',el).value)*100)}));}
function updateTotal() { $('#order-total').textContent=money(orderLines.reduce((s,i)=>s+i.quantity*i.price,0));document.querySelectorAll('[data-line]').forEach((el,n)=>$('.line-total',el).textContent=money(orderLines[n].quantity*orderLines[n].price)); }
async function orderForm(id) {
  lookups=await api('/lookups');const o=id?await api(`/orders/${id}`):{type:route,warehouse_id:1,note:'',items:[{product_id:0,quantity:1,price:0}]};orderLines=o.items.map(i=>({...i}));
  modal(`${id?'编辑':'新建'}${o.type==='purchase'?'采购单':'销售单'}`,`<form id="order-form" data-id="${id||''}" data-version="${o.version||''}" data-type="${o.type}"><div class="form-grid"><label>${o.type==='purchase'?'供应商':'客户'} *<select name="partner_id" required data-testid="field-partner_id"><option value="">请选择往来单位</option>${lookups.partners.filter(p=>p.type===(o.type==='purchase'?'supplier':'customer')&&(p.active||p.id===o.partner_id)).map(p=>option(p.id,p.name+(p.active?'':'（已停用）'),o.partner_id)).join('')}</select></label><label>仓库 *<select name="warehouse_id" data-testid="field-warehouse_id">${lookups.warehouses.map(w=>option(w.id,w.name,o.warehouse_id)).join('')}</select></label></div><h3 class="lines-title">商品明细</h3><div class="line-row line-head"><span>商品</span><span>数量</span><span>单价（元）</span><span>小计</span><span></span></div><div id="order-lines"></div>${button('+ 添加商品','add-line','','small')}<div class="total">合计 <span id="order-total"></span></div><label>备注<textarea name="note" maxlength="500" data-testid="field-note">${esc(o.note)}</textarea></label>${modalFooter('保存草稿')}</form>`);drawLines();
}
async function detail(id) {
  const o=await api(`/orders/${id}`), business=o.type==='purchase'?'buyer':'seller';let acts='';
  const act=(label,a,cls='')=>button(label,'order-action',`data-id="${id}" data-version="${o.version}" data-command="${a}"`,cls);
  if(o.status==='draft'&&can(business)) acts+=button('编辑','edit-order',`data-id="${id}"`)+act('提交审批','submit','primary');
  if(o.status==='pending'&&can()) acts+=act('驳回','reject')+act('审批通过','approve','primary');
  if(o.status==='approved'&&can('warehouse')) acts+=act(o.type==='purchase'?'确认入库':'确认出库','complete','primary');
  if(['draft','pending','approved'].includes(o.status)&&can(business)) acts+=act('取消单据','cancel','danger');
  if(o.status==='completed'&&o.paid<o.total&&can('finance')) acts+=act(o.type==='sale'?'登记收款':'登记付款','pay','primary');
  modal(`${o.type==='purchase'?'采购单':'销售单'}详情`, `<div class="row spread"><h3 class="mono">${esc(o.number)}</h3>${badge(o.status)}</div><div class="flow">${['draft','pending','approved','completed'].map((s,i)=>`${i?'<span>→</span>':''}<span class="${o.status===s?'current':''}">${statuses[s]}</span>`).join('')}</div><div class="details">${[['往来单位',o.partner],['仓库',o.warehouse],['创建人',o.creator],['创建时间',date(o.created_at)],['已结算',money(o.paid)],['待结算',money(o.total-o.paid)]].map(([k,v])=>`<div><small>${k}</small>${esc(v)}</div>`).join('')}</div>${table(['商品','数量','单价','小计'],i=>[`${esc(i.name)}<small>${esc(i.code)}</small>`,`${i.quantity} ${esc(i.unit)}`,money(i.price),money(i.quantity*i.price)],o.items)}<div class="total">合计 ${money(o.total)}</div><div class="detail-note"><span class="muted">备注：</span>${esc(o.note)||'无'}</div>${o.payments.length?`<h3 class="lines-title">结算记录</h3>${table(['登记时间','金额','备注'],p=>[date(p.created_at),money(p.amount),esc(p.note)||'—'],o.payments)}`:''}<div class="modal-footer">${button('关闭','close-modal')}${acts}</div>`);
}
function actionForm(el) {
  const {id,version,command}=el.dataset;
  const name={submit:'提交审批',approve:'审批通过',reject:'驳回单据',complete:'确认出入库',cancel:'取消单据',pay:'登记结算'}[command];
  modal(name,`<form id="action-form" data-id="${id}" data-version="${version}" data-command="${command}"><p class="muted">${command==='complete'?'确认后将按单据数量更新库存，并记录库存流水。':command==='cancel'?'取消后单据不可继续编辑、审批或出入库。':'请确认本次操作。'}</p>${command==='reject'?'<label>驳回原因 *<textarea name="reason" required maxlength="500" data-testid="field-reason"></textarea></label>':command==='pay'?`<div class="stack">${field('本次结算金额（元） *','amount','','number','required min="0.01" max="1000000000" step="0.01"')}<label>结算备注<textarea name="note" maxlength="500"></textarea></label></div>`:''}${modalFooter(name)}</form>`);
}
function adjustForm(el) {
  const r=rows.find(r=>r.product_id===Number(el.dataset.product)&&r.warehouse_id===Number(el.dataset.warehouse));
  modal('库存盘点',`<form id="adjust-form" data-product="${r.product_id}" data-warehouse="${r.warehouse_id}" data-expected="${r.quantity}"><p>${esc(r.name)} · ${esc(r.warehouse)}</p><p class="muted">当前库存：${r.quantity} ${esc(r.unit)}</p><div class="stack">${field('实盘数量 *','quantity',r.quantity,'number','required min="0" max="1000000000" step="1"')}<label>盘点原因 *<textarea name="reason" required maxlength="200" data-testid="field-reason"></textarea></label></div>${modalFooter('确认盘点')}</form>`);
}
function exportPage() {
  const t=$('table',$('#content')); if(!t) return toast('暂无可导出数据');
  const content=Array.from(t.rows).map(r=>Array.from(r.cells).filter((c,i)=>i<t.rows[0].cells.length-(t.rows[0].lastElementChild.textContent==='操作'?1:0)).map(c=>{let s=c.textContent.trim();if(/^[=+@\-\t\r]/.test(s)) s="'"+s;return '"'+s.replaceAll('"','""')+'"';}).join(',')).join('\r\n');
  const url=URL.createObjectURL(new Blob(['\ufeff'+content],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=`${paths[route][0]}-第${page}页.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('已导出当前页');
}
document.addEventListener('click',async e=>{
  const el=e.target.closest('[data-action]');if(!el)return;e.preventDefault();const a=el.dataset.action;el.disabled=true;
  try {
    if(a==='logout'){await api('/auth/logout',{method:'POST',body:{}});user=null;login();}
    else if(a==='close-modal')$('#modal').close();
    else if(a==='go-inventory')location.hash='/inventory';
    else if(a==='prev'||a==='next'){page+=a==='prev'?-1:1;await render();}
    else if(a==='clear-filters'){filters={};page=1;await render();}
    else if(a==='new-master'||a==='edit-master')await masterForm(el.dataset.id);
    else if(a==='delete-master'){const r=rows.find(r=>r.id===Number(el.dataset.id));modal('删除记录',`<form id="delete-form" data-id="${r.id}" data-version="${r.version}"><p>确认删除「${esc(r.name)}」？已被业务引用的记录不可删除。</p>${modalFooter('确认删除')}</form>`);}
    else if(a==='new-order'||a==='edit-order')await orderForm(el.dataset.id);
    else if(a==='order-detail')await detail(el.dataset.id);
    else if(a==='order-action')actionForm(el);
    else if(a==='add-line'){syncLines();if(orderLines.length>=50)throw Error('最多添加 50 行');orderLines.push({product_id:0,quantity:1,price:0});drawLines();}
    else if(a==='remove-line'){syncLines();if(orderLines.length<=1)throw Error('至少保留一行商品');orderLines.splice(Number(el.dataset.index),1);drawLines();}
    else if(a==='adjust')adjustForm(el);
    else if(a==='export-page')exportPage();
    else if(a==='reset-dialog')modal('恢复演示数据',`<form id="reset-form"><div class="notice">此操作将清除当前业务数据并使所有用户退出登录。请先导出需要保留的数据。</div><div class="lines-title">${field('输入 RESET 确认恢复','confirm','','text','required pattern="RESET" autocomplete="off"')}</div>${modalFooter('恢复初始数据')}</form>`);
  }catch(e){toast(e.message);}finally{el.disabled=false;}
});
document.addEventListener('input',e=>{if(e.target.closest('[data-line]')){syncLines();updateTotal();}});
document.addEventListener('change',e=>{if(e.target.matches('[data-line] select')){syncLines();const n=Number(e.target.closest('[data-line]').dataset.line);orderLines[n].price=lookups.products.find(p=>p.id===Number(e.target.value))?.price||0;drawLines();}});
document.addEventListener('submit',async e=>{
  e.preventDefault();const f=e.target,b=Object.fromEntries(new FormData(f)),submit=$('[type=submit],button:not([type])',f);if(submit)submit.disabled=true;
  const err=$('.error',f);if(err)err.textContent='';
  try {
    if(f.id==='login-form'){await api('/auth/login',{method:'POST',body:b});const result=await api('/auth/me');user=result.user;demo=result.demo;navigate();return;}
    if(f.id==='filter-form'){filters=b;page=1;await render();return;}
    if(f.id==='master-form'){b.active=Number(b.active);if(route==='products'){b.price=Math.round(Number(b.price)*100);b.min_stock=Number(b.min_stock);}if(f.dataset.id)b.version=Number(f.dataset.version);await api(`/${route}${f.dataset.id?'/'+f.dataset.id:''}`,{method:f.dataset.id?'PUT':'POST',body:b});}
    else if(f.id==='delete-form')await api(`/${route}/${f.dataset.id}`,{method:'DELETE',body:{version:Number(f.dataset.version)}});
    else if(f.id==='order-form'){syncLines();const body={type:f.dataset.type,partner_id:Number(b.partner_id),warehouse_id:Number(b.warehouse_id),note:b.note,items:orderLines};if(f.dataset.id)body.version=Number(f.dataset.version);await api('/orders'+(f.dataset.id?'/'+f.dataset.id:''),{method:f.dataset.id?'PUT':'POST',body});}
    else if(f.id==='action-form'){b.version=Number(f.dataset.version);if(f.dataset.command==='pay')b.amount=Math.round(Number(b.amount)*100);await api(`/orders/${f.dataset.id}/${f.dataset.command}`,{method:'POST',body:b});}
    else if(f.id==='adjust-form')await api('/inventory/adjust',{method:'POST',body:{product_id:Number(f.dataset.product),warehouse_id:Number(f.dataset.warehouse),expected_quantity:Number(f.dataset.expected),quantity:Number(b.quantity),reason:b.reason}});
    else if(f.id==='reset-form'){await api('/demo/reset',{method:'POST',body:b});$('#modal').close();user=null;login();toast('已恢复演示数据，请重新登录');return;}
    $('#modal').close();toast('操作成功');await render();
  }catch(e){if(err)err.textContent=e.message;else toast(e.message);}finally{if(submit)submit.disabled=false;}
});
window.addEventListener('hashchange',navigate);
try {const result=await api('/auth/me');user=result.user;demo=result.demo;navigate();}catch{login();}
