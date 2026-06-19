// ══════════════════════════════════════════════════════════════
//  SISTEMA DE REGISTRO DE ASISTENCIA — HGP
//  Google Apps Script — Code.gs
//  Publicar: Web App · Ejecutar como: Yo · Acceso: Cualquiera
// ══════════════════════════════════════════════════════════════

const SH_ID   = "TU_SHEET_ID";
const SH_USR  = "Usuarios";
const SH_FUNC = "Funcionarios";
const SH_REU  = "Reuniones";
const SH_ASIS = "Asistencias";
const SH_LOG  = "Auditoria";

function doPost(e) {
  const d = JSON.parse(e.postData.contents);
  const fns = {
    auth, crearReu, listarReu, listarReuActivas, listarReuAll,
    registrarAsist, listarAsist, cerrarReu,
    listarFunc, crearFunc, toggleFunc,
    listarUsers, crearUser, toggleUser,
    verificarActa
  };
  let res;
  try {
    res = fns[d.a] ? fns[d.a](d) : {ok:false, err:"Acción desconocida"};
  } catch(ex) {
    log("ERROR", d.a||"?", ex.message);
    res = {ok:false, err: ex.message};
  }
  return ContentService.createTextOutput(JSON.stringify(res))
         .setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  // Página pública de verificación de acta
  const cod = e.parameter.cod || "";
  const res = verificarActa({cod});
  const html = buildVerificacionHTML(res, cod);
  return HtmlService.createHtmlOutput(html)
         .setTitle("Verificación de Acta — HGP")
         .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

// ── AUTENTICACIÓN ──
function auth({u, p}) {
  const rows = getS(SH_USR).getDataRange().getValues();
  for (let i=1; i<rows.length; i++) {
    const [usuario, clave, nombre, cargo, area, flag, activo] = rows[i];
    if (usuario===u && clave===p && activo===true)
      return {ok:true, nombre, cargo, area, flag};
  }
  return {ok:false, err:"Credenciales incorrectas o usuario inactivo"};
}

// ── REUNIONES ──
function crearReu({memo,tema,fechaI,fechaF,lugar,convoca,obs,convocados,creador,ts}) {
  const cod = "REU-"+(Math.floor(Math.random()*9000)+1000);
  getS(SH_REU).appendRow([
    cod, memo||"", tema, fechaI, fechaF, lugar, convoca,
    obs||"", JSON.stringify(convocados||[]), creador, ts, "Abierta", ""
  ]);
  log("CREAR_REU", creador, cod);
  return {ok:true, codigo:cod};
}

function listarReu({fecha}) {
  const rows = getS(SH_REU).getDataRange().getValues();
  const lista = [];
  const f = fecha || hoy();
  for (let i=1; i<rows.length; i++) {
    const [cod,memo,tema,fechaI,fechaF,lugar,convoca,obs,convocados,,, estado] = rows[i];
    if (estado==="Abierta" && String(fechaI).startsWith(f))
      lista.push({codigo:cod, memo, tema, fechaI:String(fechaI), fechaF:String(fechaF),
                  lugar, convoca, obs, convocados:JSON.parse(convocados||"[]")});
  }
  return {ok:true, reuniones:lista};
}

function listarReuActivas() {
  const rows = getS(SH_REU).getDataRange().getValues();
  const lista = [];
  for (let i=1; i<rows.length; i++) {
    const [cod,memo,tema,fechaI,fechaF,lugar,convoca,obs,convocados,creador,ts,estado] = rows[i];
    if (estado==="Abierta")
      lista.push({codigo:cod, memo, tema, fechaI:String(fechaI), fechaF:String(fechaF),
                  lugar, convoca, obs, convocados:JSON.parse(convocados||"[]"), creador});
  }
  return {ok:true, reuniones:lista};
}

function listarReuAll() {
  const rows = getS(SH_REU).getDataRange().getValues();
  const lista = [];
  for (let i=1; i<rows.length; i++) {
    const [cod,memo,tema,fechaI,fechaF,lugar,convoca,obs,convocados,creador,ts,estado,tsCierre] = rows[i];
    lista.push({codigo:cod, memo, tema, fechaI:String(fechaI), fechaF:String(fechaF),
                lugar, convoca, obs, convocados:JSON.parse(convocados||"[]"),
                creador, ts:String(ts), estado, tsCierre:String(tsCierre||"")});
  }
  return {ok:true, reuniones:lista};
}

function cerrarReu({cod, ts}) {
  const sh = getS(SH_REU);
  const rows = sh.getDataRange().getValues();
  for (let i=1; i<rows.length; i++) {
    if (rows[i][0]===cod) {
      sh.getRange(i+1, 12).setValue("Cerrada");
      sh.getRange(i+1, 13).setValue(ts);
      log("CERRAR_REU", "sistema", cod);
      return {ok:true};
    }
  }
  return {ok:false, err:"Reunión no encontrada"};
}

// ── ASISTENCIAS ──
function registrarAsist({cod, u, nombre, cargo, ts}) {
  const shR = getS(SH_REU);
  const rRows = shR.getDataRange().getValues();
  let reu = null;
  for (let i=1; i<rRows.length; i++) {
    if (rRows[i][0]===cod && rRows[i][11]==="Abierta") {
      const convocados = JSON.parse(rRows[i][8]||"[]");
      reu = {codigo:rRows[i][0], tema:rRows[i][2], lugar:rRows[i][5], convocados};
      break;
    }
  }
  if (!reu) return {ok:false, err:"Reunión no encontrada o ya cerrada"};

  const shA = getS(SH_ASIS);
  const aRows = shA.getDataRange().getValues();
  for (let i=1; i<aRows.length; i++) {
    if (aRows[i][0]===cod && aRows[i][2]===u)
      return {ok:false, err:"Ya registraste tu asistencia en esta reunión"};
  }

  const esConv = reu.convocados.some(c=>c.nombre===nombre);
  const tipo = esConv ? "convocado" : "adicional";
  shA.appendRow([cod, reu.tema, u, nombre, cargo, ts, tipo]);
  return {ok:true, tipo, reunion:reu};
}

function listarAsist({cod}) {
  const rows = getS(SH_ASIS).getDataRange().getValues();
  const lista = [];
  for (let i=1; i<rows.length; i++) {
    if (rows[i][0]===cod)
      lista.push({nombre:rows[i][3], cargo:rows[i][4], hora:String(rows[i][5]), tipo:rows[i][6]});
  }
  return {ok:true, asistentes:lista};
}

// ── VERIFICACIÓN PÚBLICA ──
function verificarActa({cod}) {
  if (!cod) return {ok:false, err:"Código requerido"};
  const rRows = getS(SH_REU).getDataRange().getValues();
  let reu = null;
  for (let i=1; i<rRows.length; i++) {
    if (rRows[i][0]===cod) {
      reu = {
        codigo:rRows[i][0], memo:rRows[i][1], tema:rRows[i][2],
        fechaI:String(rRows[i][3]), fechaF:String(rRows[i][4]),
        lugar:rRows[i][5], convoca:rRows[i][6], obs:rRows[i][7],
        convocados:JSON.parse(rRows[i][8]||"[]"), creador:rRows[i][9],
        ts:String(rRows[i][10]), estado:rRows[i][11], tsCierre:String(rRows[i][12]||"")
      };
      break;
    }
  }
  if (!reu) return {ok:false, err:"Código de reunión no encontrado"};
  const asist = listarAsist({cod}).asistentes;
  return {ok:true, reunion:reu, asistentes:asist};
}

// ── FUNCIONARIOS ──
function listarFunc() {
  const rows = getS(SH_FUNC).getDataRange().getValues();
  const lista = [];
  for (let i=1; i<rows.length; i++) {
    const [id, nombre, cargo, area, activo] = rows[i];
    if (activo===true) lista.push({id, nombre, cargo, area});
  }
  return {ok:true, funcionarios:lista};
}

function crearFunc({nombre, cargo, area}) {
  const sh = getS(SH_FUNC);
  const id = sh.getLastRow();
  sh.appendRow([id, nombre, cargo, area||"", true]);
  return {ok:true};
}

function toggleFunc({id}) {
  const sh = getS(SH_FUNC);
  const rows = sh.getDataRange().getValues();
  for (let i=1; i<rows.length; i++) {
    if (rows[i][0]==id) {
      sh.getRange(i+1, 5).setValue(!rows[i][4]);
      return {ok:true};
    }
  }
  return {ok:false, err:"Funcionario no encontrado"};
}

// ── USUARIOS ──
function listarUsers() {
  const rows = getS(SH_USR).getDataRange().getValues();
  const lista = [];
  for (let i=1; i<rows.length; i++) {
    const [usuario,,nombre,cargo,area,flag,activo] = rows[i];
    lista.push({usuario, nombre, cargo, area, flag, activo});
  }
  return {ok:true, usuarios:lista};
}

function crearUser({u, p, nombre, cargo, area, flag}) {
  getS(SH_USR).appendRow([u, p, nombre, cargo, area||"", flag||"normal", true]);
  log("CREAR_USER", "admin", u);
  return {ok:true};
}

function toggleUser({usuario}) {
  const sh = getS(SH_USR);
  const rows = sh.getDataRange().getValues();
  for (let i=1; i<rows.length; i++) {
    if (rows[i][0]===usuario) {
      sh.getRange(i+1, 7).setValue(!rows[i][6]);
      return {ok:true};
    }
  }
  return {ok:false, err:"Usuario no encontrado"};
}

// ── UTILIDADES ──
function getS(nombre) {
  return SpreadsheetApp.openById(SH_ID).getSheetByName(nombre);
}

function hoy() {
  return Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd");
}

function log(accion, usuario, detalle) {
  try {
    getS(SH_LOG).appendRow([
      Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "dd/MM/yyyy HH:mm:ss"),
      accion, usuario, detalle
    ]);
  } catch(e) {}
}

// ── HTML VERIFICACIÓN PÚBLICA ──
function buildVerificacionHTML(res, cod) {
  if (!res.ok) {
    return `<!DOCTYPE html><html><head><meta charset="UTF-8">
    <title>Verificación — HGP</title>
    <style>body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;background:#F2F5FA;margin:0;}
    .box{background:white;border-radius:12px;padding:32px;max-width:400px;text-align:center;box-shadow:0 4px 20px rgba(0,0,0,.1);}
    .icon{font-size:48px;margin-bottom:16px;} .title{font-size:20px;font-weight:700;color:#C0392B;} .sub{color:#7D90A8;font-size:14px;margin-top:8px;}</style>
    </head><body><div class="box"><div class="icon">❌</div>
    <div class="title">Código no encontrado</div>
    <div class="sub">El código <b>${cod}</b> no corresponde a ninguna reunión registrada.</div>
    </div></body></html>`;
  }

  const r = res.reunion;
  const asist = res.asistentes || [];
  const convs = r.convocados || [];
  const asistTotal = asist.filter(a=>a.tipo==="convocado").length;
  const adic = asist.filter(a=>a.tipo==="adicional");

  const rowsConv = convs.map((c,i) => {
    const a = asist.find(x=>x.nombre===c.nombre);
    return `<tr>
      <td>${i+1}</td><td>${c.nombre}</td><td>${c.cargo}</td>
      <td style="color:${a?'#00A86B':'#C0392B'};font-weight:700">${a?'✓':'✗'}</td>
      <td>${a?a.hora:'—'}</td>
    </tr>`;
  }).join("");

  const rowsAdic = adic.map((a,i) => `<tr>
    <td>${i+1}</td><td>${a.nombre}</td><td>${a.cargo}</td><td>${a.hora}</td>
  </tr>`).join("");

  return `<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Verificación Acta ${r.codigo} — HGP</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',sans-serif;background:#F2F5FA;color:#0B2545;padding:16px}
    .header{background:linear-gradient(135deg,#0B2545,#163A6B);color:white;border-radius:12px;padding:20px;margin-bottom:16px;text-align:center}
    .header h1{font-size:16px;margin-bottom:4px}
    .header p{font-size:12px;opacity:.7}
    .badge{display:inline-block;background:#00A86B;color:white;font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;margin-top:8px}
    .card{background:white;border-radius:10px;box-shadow:0 1px 6px rgba(0,0,0,.08);padding:16px;margin-bottom:12px}
    .card h2{font-size:11px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;color:#7D90A8;margin-bottom:12px}
    .row{display:flex;gap:8px;padding:6px 0;border-bottom:1px solid #E4EAF3;font-size:13px}
    .row:last-child{border:none}
    .row label{color:#7D90A8;min-width:120px;font-size:12px}
    table{width:100%;border-collapse:collapse;font-size:12px}
    th{background:#0B2545;color:white;padding:7px 8px;text-align:left;font-size:11px}
    td{padding:7px 8px;border-bottom:1px solid #E4EAF3}
    tr:last-child td{border:none}
    tr:nth-child(even) td{background:#F8FAFD}
    .stats{display:flex;gap:10px;margin-bottom:12px}
    .stat{flex:1;background:white;border-radius:8px;padding:12px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.07)}
    .stat-n{font-size:24px;font-weight:700;color:#00A86B}
    .stat-l{font-size:11px;color:#7D90A8;margin-top:2px}
    .verified{background:#E8F8F2;border:1px solid #86EFAC;border-radius:8px;padding:12px;text-align:center;font-size:12px;color:#166534;margin-bottom:12px}
  </style>
  </head><body>
  <div class="header">
    <p>MINISTERIO DE SALUD PÚBLICA DEL ECUADOR</p>
    <h1>Hospital General Puyo</h1>
    <p>Verificación de Acta de Asistencia</p>
    <div class="badge">✓ DOCUMENTO VERIFICADO</div>
  </div>

  <div class="verified">✅ Este documento fue generado por el Sistema Institucional de Registro de Reuniones del HGP y su contenido ha sido verificado como auténtico.</div>

  <div class="card">
    <h2>Datos de la reunión</h2>
    <div class="row"><label>Código</label><span><b>${r.codigo}</b></span></div>
    ${r.memo?`<div class="row"><label>Memorando</label><span>${r.memo}</span></div>`:""}
    <div class="row"><label>Asunto</label><span>${r.tema}</span></div>
    <div class="row"><label>Fecha inicio</label><span>${r.fechaI}</span></div>
    <div class="row"><label>Hora est. fin</label><span>${r.fechaF}</span></div>
    ${r.tsCierre?`<div class="row"><label>Cierre real</label><span>${r.tsCierre}</span></div>`:""}
    <div class="row"><label>Lugar</label><span>${r.lugar}</span></div>
    <div class="row"><label>Convocado por</label><span>${r.convoca}</span></div>
    <div class="row"><label>Estado</label><span style="color:${r.estado==='Abierta'?'#00A86B':'#C0392B'};font-weight:700">${r.estado}</span></div>
  </div>

  <div class="stats">
    <div class="stat"><div class="stat-n">${convs.length}</div><div class="stat-l">Convocados</div></div>
    <div class="stat"><div class="stat-n">${asistTotal}</div><div class="stat-l">Asistieron</div></div>
    <div class="stat"><div class="stat-n">${adic.length}</div><div class="stat-l">Adicionales</div></div>
  </div>

  <div class="card">
    <h2>Sección A — Convocados</h2>
    <table><tr><th>#</th><th>Nombre</th><th>Cargo</th><th>Asistió</th><th>Hora</th></tr>
    ${rowsConv}</table>
  </div>

  ${adic.length>0?`<div class="card">
    <h2>Sección B — Asistentes adicionales</h2>
    <table><tr><th>#</th><th>Nombre</th><th>Cargo</th><th>Hora</th></tr>
    ${rowsAdic}</table>
  </div>`:""}

  <div style="text-align:center;font-size:11px;color:#7D90A8;margin-top:16px;padding-bottom:24px">
    Verificado el: ${new Date().toLocaleString('es-EC')} · Sistema HGP v1.0
  </div>
  </body></html>`;
}

// ══════════════════════════════════════════════════════════════
//  ESTRUCTURA DE HOJAS (Google Sheets)
//
//  "Usuarios":     usuario | clave | nombre | cargo | area | flag(normal/super) | activo(TRUE/FALSE)
//  "Funcionarios": id | nombre | cargo | area | activo(TRUE/FALSE)
//  "Reuniones":    codigo | memo | tema | fechaI | fechaF | lugar | convoca | obs | convocados(JSON) | creador | ts_creacion | estado | ts_cierre
//  "Asistencias":  codigo_reunion | tema | usuario | nombre | cargo | timestamp | tipo(convocado/adicional)
//  "Auditoria":    timestamp | accion | usuario | detalle
// ══════════════════════════════════════════════════════════════
