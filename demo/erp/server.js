import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { randomBytes, scryptSync, timingSafeEqual } from 'node:crypto';
import { db, all, one, run, transaction, now, audit, seed } from './db.js';

const port = Number(process.env.PORT || 8080);
const demo = process.env.DEMO_MODE !== 'false';
const fail = (status, message) => { const e = new Error(message); e.status = status; throw e; };
const str = (v, name, max = 100, required = true) => {
  if (typeof v !== 'string' || v.trim().length > max || (required && !v.trim())) fail(422, `${name}${required?'必填且':''}不能超过 ${max} 个字符`);
  return v.trim();
};
const int = (v, name, min = 0, max = 1000000) => { if (!Number.isSafeInteger(v) || v < min || v > max) fail(422, `${name}必须为 ${min}–${max} 的整数`); return v; };
const choice = (v, values, name) => { if (!values.includes(v)) fail(422, `${name}无效`); return v; };
const exists = (table, id) => one(`SELECT * FROM ${table} WHERE id=?`, int(id,'ID',1)) || fail(404, '记录不存在');
const allowed = (u, roles) => { if (u.role !== 'admin' && !roles.includes(u.role)) fail(403, '当前角色没有操作权限'); };
const version = (row, b) => { if (b.version !== row.version) fail(409,'记录已更新，请刷新后重试'); };
const orderSelect = `SELECT o.*,p.name partner,w.name warehouse,u.name creator FROM orders o JOIN partners p ON p.id=o.partner_id JOIN warehouses w ON w.id=o.warehouse_id JOIN users u ON u.id=o.created_by`;
const orderDetail = id => ({...one(`${orderSelect} WHERE o.id=?`,id),items:all('SELECT i.*,p.name,p.code,p.unit FROM order_items i JOIN products p ON p.id=i.product_id WHERE order_id=?',id),payments:all('SELECT * FROM payments WHERE order_id=? ORDER BY id DESC',id)});
function paged(rows, url) {
  const page = int(Number(url.searchParams.get('page') || 1),'页码',1,1000000);
  const size = int(Number(url.searchParams.get('pageSize') || 10),'每页条数',1,100);
  return {items: rows.slice((page-1)*size,page*size), total:rows.length, page, pageSize:size};
}
function filter(rows, url, fields) {
  const q=(url.searchParams.get('q') || '').trim().toLowerCase();
  return rows.filter(r => (!q || fields.some(f => String(r[f]??'').toLowerCase().includes(q))) && ['type','status','warehouse_id'].every(f => !url.searchParams.get(f) || String(r[f])===url.searchParams.get(f)));
}
async function body(req) {
  if (!(req.headers['content-type'] || '').startsWith('application/json')) fail(415,'请使用 application/json');
  let text=''; for await (const chunk of req) { text+=chunk; if (Buffer.byteLength(text)>1048576) fail(413,'请求体过大'); }
  try { const b=JSON.parse(text); if (!b || Array.isArray(b) || typeof b !== 'object') throw Error(); return b; } catch { fail(400,'JSON 请求格式错误'); }
}
function stock(product, warehouse, delta, reason, order, user) {
  const current = one('SELECT quantity FROM inventory WHERE product_id=? AND warehouse_id=?',product,warehouse)?.quantity || 0;
  if (current+delta<0) fail(409, `${exists('products',product).name} 库存不足，当前可用 ${current}`);
  if (current+delta>1000000000) fail(422,'库存超过上限');
  run('INSERT INTO inventory VALUES(?,?,?) ON CONFLICT(product_id,warehouse_id) DO UPDATE SET quantity=excluded.quantity',product,warehouse,current+delta);
  run('INSERT INTO movements(product_id,warehouse_id,delta,balance,reason,order_id,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)',product,warehouse,delta,current+delta,reason,order,user,now());
}
function validateOrder(b) {
  const type=choice(b.type,['purchase','sale'],'单据类型');
  const partner=exists('partners',b.partner_id); exists('warehouses',b.warehouse_id);
  if (!partner.active || partner.type !== (type==='purchase'?'supplier':'customer')) fail(422,'请选择已启用的对应往来单位');
  if (!Array.isArray(b.items) || b.items.length<1 || b.items.length>50) fail(422,'单据必须包含 1–50 行商品');
  const seen=new Set(); let total=0;
  const items=b.items.map(i => {
    if (!i || typeof i !== 'object' || Array.isArray(i)) fail(422,'商品明细格式无效');
    const p=exists('products',i.product_id); if (!p.active) fail(422,'不可选择停用商品');
    if (seen.has(p.id)) fail(422,'同一单据不可重复添加商品'); seen.add(p.id);
    const quantity=int(i.quantity,'数量',1,10000), price=int(i.price,'单价（分）',0,100000000);
    total+=quantity*price; return {product_id:p.id,quantity,price};
  });
  if (total>100000000000) fail(422,'单据总额不能超过 10 亿元');
  return {type,partner_id:partner.id,warehouse_id:b.warehouse_id,items,total,note:str(b.note??'','备注',500,false)};
}
const loginAttempts = new Map();
async function api(req,res,url) {
  const path=url.pathname, method=req.method;
  if (path==='/api/health' && method==='GET') { one('SELECT 1'); return {status:'ok',version:'1.0.0'}; }
  if (path==='/api/auth/login' && method==='POST') {
    const b=await body(req), username=str(b.username,'用户名',40), password=str(b.password,'密码',128);
    const key=`${req.socket.remoteAddress}:${username}`; const attempt=loginAttempts.get(key);
    if (attempt?.until>Date.now() && attempt.count>=10) fail(429,'登录失败次数过多，请 5 分钟后再试');
    const u=one('SELECT * FROM users WHERE username=?',username);
    const [salt,hash]=(u?.password || 'invalid:'+ '0'.repeat(128)).split(':');
    if (!timingSafeEqual(scryptSync(password,salt,64),Buffer.from(hash,'hex')) || !u) {
      if (loginAttempts.size>10000) loginAttempts.clear();
      loginAttempts.set(key,{count:attempt?.until>Date.now()?attempt.count+1:1,until:attempt?.until>Date.now()?attempt.until:Date.now()+300000});
      fail(401,'用户名或密码错误');
    }
    loginAttempts.delete(key); run('DELETE FROM sessions WHERE expires<?',Date.now());
    const token=randomBytes(32).toString('hex'); run('INSERT INTO sessions VALUES(?,?,?)',token,u.id,Date.now()+8*3600000);
    res.setHeader('Set-Cookie',`erp_session=${token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800`);
    audit(u.id,'登录','session'); return {user:{id:u.id,username:u.username,name:u.name,role:u.role}};
  }
  const token=(req.headers.cookie||'').split(';').map(s=>s.trim()).find(s=>s.startsWith('erp_session='))?.slice(12);
  const user=one('SELECT u.id,u.username,u.name,u.role FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?',token||'',Date.now());
  if (!user) fail(401,'请先登录或会话已过期');
  if (method!=='GET' && req.headers.origin && req.headers.origin !== `http://${req.headers.host}` && req.headers.origin !== `https://${req.headers.host}`) fail(403,'不允许跨站请求');
  if (path==='/api/auth/me' && method==='GET') return {user,demo};
  if (path==='/api/auth/logout' && method==='POST') { run('DELETE FROM sessions WHERE token=?',token); res.setHeader('Set-Cookie','erp_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'); return {message:'已退出登录'}; }
  if (path==='/api/lookups' && method==='GET') return {products:all('SELECT * FROM products ORDER BY id'),partners:all('SELECT * FROM partners ORDER BY id'),warehouses:all('SELECT * FROM warehouses')};
  if (path==='/api/dashboard' && method==='GET') return {
    products:one('SELECT COUNT(*) n FROM products WHERE active=1').n,
    pending:one("SELECT COUNT(*) n FROM orders WHERE status IN ('pending','approved')").n,
    sales:one("SELECT COALESCE(SUM(total),0) n FROM orders WHERE type='sale' AND status='completed'").n,
    purchases:one("SELECT COALESCE(SUM(total),0) n FROM orders WHERE type='purchase' AND status='completed'").n,
    receivable:one("SELECT COALESCE(SUM(total-paid),0) n FROM orders WHERE type='sale' AND status='completed'").n,
    payable:one("SELECT COALESCE(SUM(total-paid),0) n FROM orders WHERE type='purchase' AND status='completed'").n,
    lowStock:all('SELECT p.id,p.code,p.name,p.unit,p.min_stock,w.name warehouse,COALESCE(i.quantity,0) quantity FROM products p CROSS JOIN warehouses w LEFT JOIN inventory i ON p.id=i.product_id AND w.id=i.warehouse_id WHERE p.active=1 AND COALESCE(i.quantity,0)<p.min_stock ORDER BY quantity LIMIT 10'),
    recent:all(`${orderSelect} ORDER BY o.id DESC LIMIT 6`),
    trend:all("SELECT substr(created_at,1,10) day,SUM(CASE WHEN type='sale' THEN total ELSE 0 END) sales,SUM(CASE WHEN type='purchase' THEN total ELSE 0 END) purchases FROM orders WHERE status='completed' AND created_at>=date('now','-6 days') GROUP BY day ORDER BY day")
  };
  const master=path.match(/^\/api\/(products|partners)(?:\/(\d+))?$/);
  if (master) {
    const table=master[1], id=Number(master[2]);
    if (method==='GET') return id?exists(table,id):paged(filter(all(`SELECT * FROM ${table} ORDER BY id DESC`),url,['code','name','category','contact','phone']),url);
    allowed(user, table==='products'?['buyer','warehouse']:['buyer','seller']);
    const b=await body(req);
    return transaction(()=>{
      const old=id?exists(table,id):null; if (old) version(old,b);
      if (method==='DELETE') {
        allowed(user,[]);
        if (!old) fail(404,'记录不存在');
        const used=table==='products'?one('SELECT id FROM order_items WHERE product_id=? LIMIT 1',id)||one('SELECT id FROM movements WHERE product_id=? LIMIT 1',id):one('SELECT id FROM orders WHERE partner_id=? LIMIT 1',id);
        if (used) fail(409,'记录已被业务引用，请改为停用');
        if (table==='products') run('DELETE FROM inventory WHERE product_id=?',id);
        run(`DELETE FROM ${table} WHERE id=?`,id); audit(user.id,'删除',`${table}/${id}`); return {message:'已删除'};
      }
      if (!['POST','PUT'].includes(method) || (method==='PUT'&&!id) || (method==='POST'&&id)) fail(405,'不支持此方法');
      const code=str(b.code,'编码',30); if (!/^[A-Za-z0-9_-]+$/.test(code)) fail(422,'编码只允许字母、数字、下划线和短横线');
      const name=str(b.name,'名称',100), active=int(b.active??1,'启用状态',0,1);
      let columns, values;
      if (table==='products') { columns=['code','name','category','unit','price','min_stock','active']; values=[code,name,str(b.category,'分类',30),str(b.unit,'单位',10),int(b.price,'单价（分）',0,100000000),int(b.min_stock,'安全库存',0,1000000),active]; }
      else {
        const type=choice(b.type,['customer','supplier'],'单位类型');
        if (user.role==='buyer' && (type!=='supplier'||(old&&old.type!=='supplier')) || user.role==='seller'&&(type!=='customer'||(old&&old.type!=='customer'))) fail(403,'仅能维护本角色对应的往来单位');
        if (old && old.type!==type && one('SELECT id FROM orders WHERE partner_id=?',id)) fail(409,'已被引用的单位不能改变类型');
        const phone=str(b.phone??'','电话',30,false); if (phone && !/^[+\d()\s-]{5,30}$/.test(phone)) fail(422,'电话格式无效');
        columns=['code','name','type','contact','phone','active']; values=[code,name,type,str(b.contact??'','联系人',50,false),phone,active];
      }
      let rid=id;
      if (old) run(`UPDATE ${table} SET ${columns.map(c=>c+'=?').join(',')},version=version+1 WHERE id=?`,...values,id);
      else rid=Number(run(`INSERT INTO ${table}(${columns.join(',')}) VALUES(${columns.map(()=>'?').join(',')})`,...values).lastInsertRowid);
      audit(user.id,old?'修改':'新增',`${table}/${rid}`,name); return exists(table,rid);
    });
  }
  if (path==='/api/orders' && method==='GET') return paged(filter(all(`${orderSelect} ORDER BY o.id DESC`),url,['number','partner','note']),url);
  const match=path.match(/^\/api\/orders(?:\/(\d+))?(?:\/(submit|approve|reject|complete|cancel|pay))?$/);
  if (match) {
    const id=Number(match[1]),action=match[2];
    if (method==='GET' && id && !action) { exists('orders',id); return orderDetail(id); }
    if (!['POST','PUT'].includes(method)) fail(405,'不支持此方法');
    const b=await body(req);
    return transaction(()=>{
      const old=id?exists('orders',id):null;
      if (old) version(old,b);
      if (!action) {
        if ((id && method!=='PUT') || (!id && method!=='POST')) fail(405,'不支持此方法');
        const data=validateOrder(b); allowed(user,data.type==='purchase'?['buyer']:['seller']);
        if (old && (old.status!=='draft' || old.type!==data.type)) fail(409,'仅能编辑同类型草稿单据');
        let rid=id;
        if (old) { run('UPDATE orders SET partner_id=?,warehouse_id=?,total=?,note=?,version=version+1 WHERE id=?',data.partner_id,data.warehouse_id,data.total,data.note,id); run('DELETE FROM order_items WHERE order_id=?',id); }
        else {
          const num=`${data.type==='purchase'?'PO':'SO'}-${new Date().toISOString().slice(0,10).replaceAll('-','')}-${randomBytes(4).toString('hex').toUpperCase()}`;
          rid=Number(run('INSERT INTO orders(number,type,partner_id,warehouse_id,total,note,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)',num,data.type,data.partner_id,data.warehouse_id,data.total,data.note,user.id,now()).lastInsertRowid);
        }
        for (const i of data.items) run('INSERT INTO order_items(order_id,product_id,quantity,price) VALUES(?,?,?,?)',rid,i.product_id,i.quantity,i.price);
        audit(user.id,old?'编辑单据':'创建单据',`orders/${rid}`); return orderDetail(rid);
      }
      if (method!=='POST' || !old) fail(405,'不支持此方法');
      const businessRole=old.type==='purchase'?'buyer':'seller'; let next;
      if (action==='submit') { allowed(user,[businessRole]); if (old.status!=='draft') fail(409,'仅草稿可提交'); next='pending'; }
      if (action==='approve'||action==='reject') { allowed(user,[]); if(old.status!=='pending') fail(409,'仅待审批单据可审批'); next=action==='approve'?'approved':'draft'; }
      if (action==='cancel') { allowed(user,[businessRole]); if (!['draft','pending','approved'].includes(old.status)) fail(409,'当前单据不可取消'); next='cancelled'; }
      if (action==='complete') {
        allowed(user,['warehouse']); if(old.status!=='approved') fail(409,'仅已审批单据可出入库');
        for (const i of all('SELECT * FROM order_items WHERE order_id=?',id)) stock(i.product_id,old.warehouse_id,old.type==='purchase'?i.quantity:-i.quantity,old.type==='purchase'?'采购入库':'销售出库',id,user.id);
        next='completed';
      }
      if (action==='pay') {
        allowed(user,['finance']); if(old.status!=='completed') fail(409,'仅已完成单据可结算');
        const amount=int(b.amount,'金额（分）',1,100000000000); if(amount>old.total-old.paid) fail(409,'金额不能超过未结算金额');
        const note=str(b.note??'','结算备注',500,false);
        run('INSERT INTO payments(order_id,amount,note,created_by,created_at) VALUES(?,?,?,?,?)',id,amount,note,user.id,now());
        run('UPDATE orders SET paid=paid+?,version=version+1 WHERE id=?',amount,id);
      } else run('UPDATE orders SET status=?,version=version+1 WHERE id=?',next,id);
      const reason=action==='reject'?str(b.reason,'驳回原因',500):'';
      audit(user.id,action,`orders/${id}`,reason); return orderDetail(id);
    });
  }
  if (path==='/api/inventory' && method==='GET') {
    let rows=filter(all('SELECT p.id product_id,p.code,p.name,p.unit,p.min_stock,p.active,w.id warehouse_id,w.name warehouse,COALESCE(i.quantity,0) quantity FROM products p CROSS JOIN warehouses w LEFT JOIN inventory i ON i.product_id=p.id AND i.warehouse_id=w.id ORDER BY p.id,w.id'),url,['code','name','warehouse']);
    if(url.searchParams.get('low')==='1') rows=rows.filter(r=>r.active && r.quantity<r.min_stock);
    return paged(rows,url);
  }
  if (path==='/api/inventory/adjust' && method==='POST') {
    allowed(user,['warehouse']); const b=await body(req); exists('products',b.product_id); exists('warehouses',b.warehouse_id);
    const quantity=int(b.quantity,'盘点数量',0,1000000000), expected=int(b.expected_quantity,'原库存',0,1000000000), reason=str(b.reason,'盘点原因',200);
    return transaction(()=>{
      const old=one('SELECT quantity FROM inventory WHERE product_id=? AND warehouse_id=?',b.product_id,b.warehouse_id)?.quantity || 0;
      if (old!==expected) fail(409,'库存已变化，请刷新后重新盘点'); if(old===quantity) fail(422,'盘点数量与原库存相同');
      stock(b.product_id,b.warehouse_id,quantity-old,`盘点：${reason}`,null,user.id); audit(user.id,'盘点','inventory',reason); return {message:'盘点完成'};
    });
  }
  if (path==='/api/movements' && method==='GET') return paged(filter(all('SELECT m.*,p.code,p.name,w.name warehouse,u.name operator,o.number order_number FROM movements m JOIN products p ON p.id=m.product_id JOIN warehouses w ON w.id=m.warehouse_id JOIN users u ON u.id=m.created_by LEFT JOIN orders o ON o.id=m.order_id ORDER BY m.id DESC'),url,['code','name','reason','order_number']),url);
  if (path==='/api/payments' && method==='GET') { allowed(user,['finance','viewer']); return paged(all('SELECT p.*,o.number,o.type,u.name operator FROM payments p JOIN orders o ON o.id=p.order_id JOIN users u ON u.id=p.created_by ORDER BY p.id DESC'),url); }
  if (path==='/api/audit' && method==='GET') { allowed(user,['viewer']); return paged(filter(all('SELECT a.*,u.name operator FROM audit a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC'),url,['action','entity','detail','operator']),url); }
  if (path==='/api/users' && method==='GET') { allowed(user,[]); return all('SELECT id,username,name,role FROM users ORDER BY id'); }
  if (path==='/api/demo/reset' && method==='POST') { allowed(user,[]); if(!demo) fail(403,'演示数据重置已禁用'); const b=await body(req); if(b.confirm!=='RESET') fail(422,'请输入 RESET 确认'); seed(true); loginAttempts.clear(); return {message:'演示数据已恢复，请重新登录'}; }
  fail(404,'接口不存在');
}
const staticFiles = {'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css','/favicon.svg':'favicon.svg'};
const server=http.createServer(async(req,res)=>{
  res.setHeader('X-Content-Type-Options','nosniff'); res.setHeader('X-Frame-Options','DENY');
  res.setHeader('Referrer-Policy','same-origin');
  res.setHeader('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
  try {
    const url=new URL(req.url,'http://localhost');
    if(url.pathname.startsWith('/api/')) { res.setHeader('Content-Type','application/json; charset=utf-8'); res.setHeader('Cache-Control','no-store'); const result=await api(req,res,url); res.end(JSON.stringify(result)); return; }
    if(req.method!=='GET') fail(405,'不支持此方法');
    const file=staticFiles[url.pathname]; if(!file) fail(404,'页面不存在');
    res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript; charset=utf-8':file.endsWith('.css')?'text/css; charset=utf-8':file.endsWith('.svg')?'image/svg+xml':'text/html; charset=utf-8');
    res.setHeader('Cache-Control','no-cache'); res.end(await readFile(fileURLToPath(new URL(`./public/${file}`,import.meta.url))));
  } catch(e) {
    const conflict=e.code?.startsWith('SQLITE_CONSTRAINT') || e.message?.includes('UNIQUE constraint failed');
    const status=e.status || (conflict?409:500);
    if(status===500) console.error(e);
    res.statusCode=status; res.setHeader('Content-Type','application/json; charset=utf-8'); res.end(JSON.stringify({error:{code:status,message:conflict?'编码已存在或记录被引用':status===500?'服务器内部错误':e.message}}));
  }
});
server.listen(port,process.env.HOST || '127.0.0.1',()=>console.log(`启航 ERP: http://${process.env.HOST || '127.0.0.1'}:${port}`));
for (const sig of ['SIGTERM','SIGINT']) process.on(sig,()=>server.close(()=>{db.close();process.exit(0);}));
