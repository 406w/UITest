import { DatabaseSync } from 'node:sqlite';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { randomBytes, scryptSync } from 'node:crypto';

const dir = resolve(process.env.DATA_DIR || './data');
mkdirSync(dir, { recursive: true });
export const db = new DatabaseSync(resolve(dir, 'erp.sqlite'));
db.exec(`PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL, password TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL, unit TEXT NOT NULL, price INTEGER NOT NULL CHECK(price>=0), min_stock INTEGER NOT NULL CHECK(min_stock>=0), active INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS partners(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, type TEXT NOT NULL CHECK(type IN ('customer','supplier')), contact TEXT NOT NULL, phone TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS warehouses(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS inventory(product_id INTEGER NOT NULL REFERENCES products(id), warehouse_id INTEGER NOT NULL REFERENCES warehouses(id), quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity>=0), PRIMARY KEY(product_id,warehouse_id));
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT UNIQUE NOT NULL, type TEXT NOT NULL CHECK(type IN ('purchase','sale')), partner_id INTEGER NOT NULL REFERENCES partners(id), warehouse_id INTEGER NOT NULL REFERENCES warehouses(id), status TEXT NOT NULL DEFAULT 'draft', total INTEGER NOT NULL, paid INTEGER NOT NULL DEFAULT 0, note TEXT NOT NULL, created_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS order_items(id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL REFERENCES orders(id), product_id INTEGER NOT NULL REFERENCES products(id), quantity INTEGER NOT NULL CHECK(quantity>0), price INTEGER NOT NULL CHECK(price>=0));
CREATE TABLE IF NOT EXISTS movements(id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER NOT NULL REFERENCES products(id), warehouse_id INTEGER NOT NULL REFERENCES warehouses(id), delta INTEGER NOT NULL, balance INTEGER NOT NULL, reason TEXT NOT NULL, order_id INTEGER REFERENCES orders(id), created_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL REFERENCES orders(id), amount INTEGER NOT NULL CHECK(amount>0), note TEXT NOT NULL, created_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id), action TEXT NOT NULL, entity TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
CREATE INDEX IF NOT EXISTS idx_movements_product ON movements(product_id,warehouse_id);
`);
export const now = () => new Date().toISOString();
export const all = (sql, ...p) => db.prepare(sql).all(...p);
export const one = (sql, ...p) => db.prepare(sql).get(...p);
export const run = (sql, ...p) => db.prepare(sql).run(...p);
export function transaction(fn) { db.exec('BEGIN IMMEDIATE'); try { const result = fn(); db.exec('COMMIT'); return result; } catch(e) { db.exec('ROLLBACK'); throw e; } }
export function hashPassword(value) { const salt = randomBytes(16).toString('hex'); return `${salt}:${scryptSync(value, salt, 64).toString('hex')}`; }
export function audit(user, action, entity, detail = '') { run('INSERT INTO audit(user_id,action,entity,detail,created_at) VALUES(?,?,?,?,?)', user, action, entity, detail, now()); }

export function seed(reset = false) {
  transaction(() => {
    if (reset) {
      for (const table of ['sessions','payments','movements','order_items','orders','inventory','audit','products','partners','warehouses','users']) db.exec(`DELETE FROM ${table}`);
      db.exec('DELETE FROM sqlite_sequence');
    }
    if (one('SELECT id FROM users LIMIT 1')) return;
    for (const [username, name, role] of [['admin','系统管理员','admin'],['buyer','采购专员','buyer'],['seller','销售专员','seller'],['warehouse','仓库管理员','warehouse'],['finance','财务专员','finance'],['viewer','只读观察员','viewer']]) run('INSERT INTO users(username,name,role,password) VALUES(?,?,?,?)', username, name, role, hashPassword('Erp123456!'));
    run('INSERT INTO warehouses VALUES(1,?),(2,?)', '上海主仓', '杭州分仓');
    const products = [
      ['P001','商务笔记本电脑','电脑设备','台',569900,10,36], ['P002','27 英寸 4K 显示器','电脑设备','台',189900,15,24],
      ['P003','无线机械键盘','办公配件','件',39900,20,68], ['P004','无线静音鼠标','办公配件','件',12900,30,18],
      ['P005','USB-C 扩展坞','办公配件','件',26900,15,42], ['P006','人体工学办公椅','办公家具','把',89900,10,8],
      ['P007','升降办公桌','办公家具','张',159900,5,12], ['P008','A4 复印纸（5 包）','办公耗材','箱',12500,25,90],
      ['P009','激光打印机','电脑设备','台',149900,8,16], ['P010','网络交换机 8 口','网络设备','台',29900,10,22],
      ['P011','千兆无线路由器','网络设备','台',45900,10,6], ['P012','视频会议摄像头','电脑设备','台',69900,8,14]
    ];
    for (const [code,name,category,unit,price,min,stock] of products) {
      const id = Number(run('INSERT INTO products(code,name,category,unit,price,min_stock) VALUES(?,?,?,?,?,?)',code,name,category,unit,price,min).lastInsertRowid);
      for (const [wid,qty] of [[1,stock],[2,Math.floor(stock/3)]]) {
        run('INSERT INTO inventory VALUES(?,?,?)',id,wid,qty);
        run('INSERT INTO movements(product_id,warehouse_id,delta,balance,reason,created_by,created_at) VALUES(?,?,?,?,?,1,?)',id,wid,qty,qty,'期初库存',now());
      }
    }
    for (const p of [['S001','上海联创数码科技','supplier','陈经理','13800138001'],['S002','杭州优品办公用品','supplier','李经理','13800138002'],['C001','星河设计工作室','customer','林女士','13900139001'],['C002','远山信息技术有限公司','customer','周先生','13900139002'],['C003','青禾文化传媒','customer','吴女士','13900139003']]) run('INSERT INTO partners(code,name,type,contact,phone) VALUES(?,?,?,?,?)',...p);
    // Unposted seed orders leave the opening-stock ledger fully reconcilable.
    for (const [type,partner,status,product,qty] of [['purchase',1,'pending',1,5],['sale',3,'draft',3,8],['sale',4,'approved',2,3],['purchase',2,'draft',8,20]]) {
      const price = one('SELECT price FROM products WHERE id=?',product).price;
      const id = Number(run('INSERT INTO orders(number,type,partner_id,warehouse_id,status,total,note,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)',`${type==='sale'?'SO':'PO'}-DEMO-${product}`,type,partner,1,status,price*qty,'演示业务单据',1,now()).lastInsertRowid);
      run('INSERT INTO order_items(order_id,product_id,quantity,price) VALUES(?,?,?,?)',id,product,qty,price);
    }
    audit(1,'初始化','system','已创建演示数据');
  });
}
seed();
