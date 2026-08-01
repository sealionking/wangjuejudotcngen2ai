# -*- coding: utf-8 -*-
"""
地区经济治理结构差距量化 —— 多口径 Fdamage 相对距离矩阵。
零外部依赖：纯原生 Canvas 2D + 内联 CSS/JS，单文件离线可渲染。
"""
import json, os, subprocess, tempfile

# ---------- 1. 省级四口径数据(2023) ----------
# A非私营 / A2私营 / B全口径(官方或估算) / C全体居民人均可支配收入 / D最低工资首档(元/月)
# 来源:国家统计局、各省统计局、人社部(截至2023-10-01最低工资)
PROV = {
    # name: [非私营, 私营, 全口径, 可支配, 最低工资月, 常住人口万]
    "上海": [229337, 111347, 147684, 84834, 2690, 2487],
    "北京": [218312, 105931, 162122, 81752, 2420, 2186],   # 全口径估算(非私+私)/2
    "天津": [138007, 72966,  105487, 51271, 2180, 1364],
    "河北": [94818,  51281,  73050,  32903, 2200, 7393],
    "江苏": [125102, 75088,  100095, 52674, 2280, 8526],
    "浙江": [133045, 74325,  103685, 63830, 2280, 6627],
    "广东": [131418, 80685,  106052, 49327, 2300, 12706],
    "湖南": [97015,  60277,  80532,  35895, 1930, 9705],
    "四川": [110160, 62105,  90220,  32514, 2100, 8074],
    "重庆": [113653, 63941,  87169,  37595, 2100, 3213],
}
NATIONAL = {"非私营": 120698, "私营": 68340, "可支配": 39218}

# 都市圈构成(省级常住人口加权)
CLUSTERS = [
    {"name":"长三角","parts":[("上海","上海"),("江苏","江苏"),("浙江","浙江")],"note":"沪苏浙加权"},
    {"name":"珠三角","parts":[("广东","广东")],"note":"广东省(珠三角九市实际更高)"},
    {"name":"京津冀","parts":[("北京","北京"),("天津","天津"),("河北","河北")],"note":"京津冀加权"},
    {"name":"成渝","parts":[("四川","四川"),("重庆","重庆")],"note":"川渝加权"},
    {"name":"长株潭","parts":[("湖南","湖南")],"note":"湖南省代理(长株潭核心实际高于全省)"},
]

CALIBERS = ["非私营","全口径","可支配","最低工资年"]

def wavg(parts, key):
    tot = sum(PROV[p][5] for _,p in parts)
    return sum(PROV[p][key]*PROV[p][5] for _,p in parts)/tot

# 计算各都市圈四口径值
rows = []
for c in CLUSTERS:
    r = {"name":c["name"],"note":c["note"]}
    r["非私营"] = round(wavg(c["parts"],0))
    r["全口径"] = round(wavg(c["parts"],2))
    r["可支配"] = round(wavg(c["parts"],3))
    r["最低工资年"] = round(wavg(c["parts"],4)*12)
    rows.append(r)

# 上海单点(基准参照之二)
SH = {"非私营":229337,"全口径":147684,"可支配":84834,"最低工资年":2690*12}

# ---------- 2. 距离矩阵(以长三角为基准=0) ----------
BASE = rows[0]  # 长三角
def dist(w, base): return (w-base)/base*100

matrix = []
for r in rows:
    m = {"name":r["name"],"note":r["note"],"vals":{}}
    for k in CALIBERS:
        m["vals"][k] = round(dist(r[k], BASE[k]),1)
    # vs 上海单点距离
    m["vsSH"] = {k: round(dist(r[k], SH[k]),1) for k in CALIBERS}
    matrix.append(m)

# 湖南vs各地 关键距离(用非私营与可支配两口径, 量化"差多远")
targets = {"广东":PROV["广东"],"上海":PROV["上海"],"四川":PROV["四川"],"北京":PROV["北京"]}
hunan = PROV["湖南"]
vs_targets = []
for tn,td in targets.items():
    vs_targets.append({
        "target":tn,
        "非私营":round((hunan[0]-td[0])/td[0]*100,1),
        "可支配":round((hunan[3]-td[3])/td[3]*100,1),
        "最低工资":round((hunan[4]-td[4])/td[4]*100,1),
    })

# 稳健性:每都市圈四口径距离的区间
ranges = []
for m in matrix:
    vals = [m["vals"][k] for k in CALIBERS]
    ranges.append({"name":m["name"], "min":min(vals),"max":max(vals),"vals":vals})

# ---------- 3. 生成 HTML ----------
data_json = json.dumps({
    "calibers":CALIBERS,
    "matrix":matrix,
    "rows":rows,
    "base":{k:BASE[k] for k in CALIBERS},
    "sh":SH,
    "vs_targets":vs_targets,
    "ranges":ranges,
    "national":NATIONAL,
}, ensure_ascii=False)

JS_CODE = r"""
(function(){
  var D=window.__FDATA__;
  var calibers=D.calibers, matrix=D.matrix, rows=D.rows, base=D.base, sh=D.sh;
  var vs_targets=D.vs_targets, ranges=D.ranges;

  function fmt(n,d){d=(d==null)?1:d;return n.toFixed(d);}
  function pct(v,d){d=(d==null)?1:d;var s=v.toFixed(d);return (v>=0?'+':'')+s+'%';}
  function money(n){return Math.round(n).toLocaleString('en-US');}

  // 距离->颜色: 0(优)绿 -> -15(中)琥珀 -> -45+(差)深红
  function dColor(v){
    var t=(v+50)/50; if(t<0)t=0; if(t>1)t=1;
    function lerp(a,b,p){return [a[0]+(b[0]-a[0])*p,a[1]+(b[1]-a[1])*p,a[2]+(b[2]-a[2])*p];}
    var c0=[185,28,28],c1=[217,119,6],c2=[16,185,129];
    var col = t<0.6 ? lerp(c0,c1,t/0.6) : lerp(c1,c2,(t-0.6)/0.4);
    return 'rgb('+Math.round(col[0])+','+Math.round(col[1])+','+Math.round(col[2])+')';
  }

  // ===== 图1: 距离矩阵热力图 =====
  function drawHeatmap(canvas){
    var ctx=canvas.getContext('2d');
    var W=canvas.width,H=canvas.height;
    ctx.clearRect(0,0,W,H); ctx.fillStyle='#141a26'; ctx.fillRect(0,0,W,H);
    var padL=120,padR=40,padT=80,padB=70;
    var plotW=W-padL-padR, plotH=H-padT-padB;
    var nC=calibers.length, nR=matrix.length;
    var cw=plotW/nC, ch=plotH/nR;

    // 标题
    ctx.fillStyle='#e6e6e6'; ctx.font='bold 16px "Microsoft YaHei",sans-serif'; ctx.textAlign='left';
    ctx.fillText('图1  地区治理结构差距矩阵  (相对长三角基准 = 0，负值=差距)', padL, 34);
    ctx.font='12px "Microsoft YaHei",sans-serif'; ctx.fillStyle='#8a93a6';
    ctx.fillText('每格=该口径下该都市圈相对长三角的偏离%   颜色越红差距越大', padL, 52);

    // 列头
    ctx.font='bold 12px "Microsoft YaHei",sans-serif'; ctx.fillStyle='#cfd6e4'; ctx.textAlign='center';
    for(var j=0;j<nC;j++){
      var cx=padL+cw*(j+0.5);
      ctx.fillText(calibers[j], cx, padT-10);
      ctx.font='10px "Microsoft YaHei",sans-serif'; ctx.fillStyle='#8a93a6';
      ctx.fillText('基准'+money(base[calibers[j]]), cx, padT-26);
      ctx.font='bold 12px "Microsoft YaHei",sans-serif'; ctx.fillStyle='#cfd6e4';
    }
    // 行头
    ctx.textAlign='right';
    for(var i=0;i<nR;i++){
      var cy=padT+ch*(i+0.5);
      ctx.font='bold 13px "Microsoft YaHei",sans-serif'; ctx.fillStyle='#e6e6e6';
      ctx.fillText(matrix[i].name, padL-12, cy-2);
      ctx.font='10px "Microsoft YaHei",sans-serif'; ctx.fillStyle='#6b7488';
      ctx.fillText(matrix[i].note, padL-12, cy+12);
    }
    // 单元格
    ctx.textAlign='center'; ctx.font='bold 14px Consolas,monospace';
    for(var i=0;i<nR;i++){
      for(var j=0;j<nC;j++){
        var v=matrix[i].vals[calibers[j]];
        var x=padL+cw*j, y=padT+ch*i;
        ctx.fillStyle=dColor(v);
        ctx.fillRect(x+2,y+2,cw-4,ch-4);
        ctx.fillStyle = v<-25?'#fff':(v<-10?'#fff':'#1a1f2e');
        ctx.fillText(pct(v), x+cw/2, y+ch/2+5);
      }
    }
    // 图例
    ctx.textAlign='left'; ctx.font='11px "Microsoft YaHei",sans-serif';
    for(var k=0;k<=5;k++){
      var vv=-k*10; var xx=padL+plotW*0.05+k*70;
      ctx.fillStyle=dColor(vv); ctx.fillRect(xx,H-30,16,12);
      ctx.fillStyle='#8a93a6'; ctx.fillText(vv+'%',xx+20,H-20);
    }
  }

  // ===== 图2: 四口径距离区间(稳健性) =====
  function drawRange(canvas){
    var ctx=canvas.getContext('2d');
    var W=canvas.width,H=canvas.height;
    ctx.clearRect(0,0,W,H); ctx.fillStyle='#141a26'; ctx.fillRect(0,0,W,H);
    var padL=130,padR=60,padT=80,padB=60;
    var plotW=W-padL-padR, plotH=H-padT-padB;
    var n=ranges.length;
    var gap=plotH/n, barH=gap*0.5;
    var vmin=-50, vmax=5;
    function xOf(v){return padL+(v-vmin)/(vmax-vmin)*plotW;}
    var x0=xOf(0);

    ctx.fillStyle='#e6e6e6'; ctx.font='bold 16px "Microsoft YaHei",sans-serif'; ctx.textAlign='left';
    ctx.fillText('图2  四口径距离区间  (稳健性检验)', padL, 34);
    ctx.font='12px "Microsoft YaHei",sans-serif'; ctx.fillStyle='#8a93a6';
    ctx.fillText('横线=该都市圈在四口径下距离长三角的范围;点=各口径值;区间越宽说明口径越敏感', padL, 52);

    // 网格
    ctx.strokeStyle='#2a3346'; ctx.fillStyle='#8a93a6'; ctx.font='11px Consolas,monospace'; ctx.textAlign='center';
    for(var t=-50;t<=5;t+=5){
      var x=xOf(t); ctx.beginPath(); ctx.moveTo(x,padT); ctx.lineTo(x,padT+plotH); ctx.stroke();
      if(t%10==0) ctx.fillText(t+'%', x, padT+plotH+16);
    }
    ctx.strokeStyle='#5a6478'; ctx.lineWidth=2;
    ctx.beginPath(); ctx.moveTo(x0,padT-6); ctx.lineTo(x0,padT+plotH+6); ctx.stroke();

    for(var i=0;i<n;i++){
      var r=ranges[i]; var y=padT+i*gap+gap/2;
      // 区间线
      ctx.strokeStyle=dColor((r.min+r.max)/2); ctx.lineWidth=3;
      ctx.beginPath(); ctx.moveTo(xOf(r.min),y); ctx.lineTo(xOf(r.max),y); ctx.stroke();
      // 各口径点
      for(var k=0;k<4;k++){
        var v=r.vals[k];
        ctx.fillStyle=dColor(v);
        ctx.beginPath(); ctx.arc(xOf(v),y,6,0,Math.PI*2); ctx.fill();
        ctx.strokeStyle='#0e1320'; ctx.lineWidth=1.5; ctx.stroke();
      }
      // 名字
      ctx.fillStyle='#e6e6e6'; ctx.font='bold 13px "Microsoft YaHei",sans-serif'; ctx.textAlign='right';
      ctx.fillText(r.name, padL-12, y+5);
      // 区间标注
      ctx.fillStyle='#f5b942'; ctx.font='bold 11px Consolas,monospace'; ctx.textAlign='left';
      ctx.fillText('['+r.min.toFixed(1)+'% , '+r.max.toFixed(1)+'%]', xOf(r.max)+10, y+5);
    }
    // 图例
    ctx.font='11px "Microsoft YaHei",sans-serif'; ctx.textAlign='left'; ctx.fillStyle='#cfd6e4';
    var lx=padL;
    ['非私营','全口径','可支配','最低工资'].forEach(function(lbl,idx){
      ctx.fillStyle=['#b91c1c','#d97706','#0d9488','#2563eb'][idx];
      ctx.beginPath(); ctx.arc(lx+8,H-20,6,0,Math.PI*2); ctx.fill();
      ctx.fillStyle='#cfd6e4'; ctx.fillText(lbl,lx+20,H-16); lx+=90;
    });
  }

  // ===== 图3: 湖南vs各地 距离柱状 =====
  function drawVsTarget(canvas){
    var ctx=canvas.getContext('2d');
    var W=canvas.width,H=canvas.height;
    ctx.clearRect(0,0,W,H); ctx.fillStyle='#141a26'; ctx.fillRect(0,0,W,H);
    var padL=60,padR=30,padT=80,padB=70;
    var plotW=W-padL-padR, plotH=H-padT-padB;
    var n=vs_targets.length, g=3; // 3口径
    var groupW=plotW/n, barW=groupW*0.22;
    var vmax=0, vmin=-65;
    function yOf(v){return padT+plotH-(v-vmin)/(vmax-vmin)*plotH;}
    var y0=yOf(0);

    ctx.fillStyle='#e6e6e6'; ctx.font='bold 16px "Microsoft YaHei",sans-serif'; ctx.textAlign='left';
    ctx.fillText('图3  湖南 vs 各地 差距量化  (湖南比对方低几个百分点)', padL, 34);
    ctx.font='12px "Microsoft YaHei",sans-serif'; ctx.fillStyle='#8a93a6';
    ctx.fillText('直接回答"湖南比广东/上海/成渝/首都差多远"   三口径交叉', padL, 52);

    // 网格
    ctx.strokeStyle='#2a3346'; ctx.fillStyle='#8a93a6'; ctx.font='11px Consolas,monospace'; ctx.textAlign='right';
    for(var t=-60;t<=0;t+=10){
      var y=yOf(t); ctx.beginPath(); ctx.moveTo(padL,y); ctx.lineTo(padL+plotW,y); ctx.stroke();
      ctx.fillText(t+'%', padL-6, y+3);
    }
    // 0线
    ctx.strokeStyle='#5a6478'; ctx.lineWidth=1.5;
    ctx.beginPath(); ctx.moveTo(padL,y0); ctx.lineTo(padL+plotW,y0); ctx.stroke();

    var cols=['#b91c1c','#0d9488','#2563eb'];
    var lbls=['非私营工资','可支配收入','最低工资'];
    for(var i=0;i<n;i++){
      var t=vs_targets[i];
      var gx=padL+groupW*i+groupW/2;
      for(var k=0;k<g;k++){
        var key=['非私营','可支配','最低工资'][k];
        var v=t[key];
        var y=yOf(v); var h=y0-y;
        ctx.fillStyle=cols[k];
        ctx.fillRect(gx-barW*1.5+k*barW - barW/2 + barW*1.5, y, barW, h);
        // 数值
        ctx.fillStyle='#e6e6e6'; ctx.font='bold 10px Consolas,monospace'; ctx.textAlign='center';
        ctx.fillText(v+'%', gx-barW*1.5+k*barW + barW*1.5 - barW/2 + barW*1.5, y-4);
      }
      // 目标名
      ctx.fillStyle='#cfd6e4'; ctx.font='bold 13px "Microsoft YaHei",sans-serif'; ctx.textAlign='center';
      ctx.fillText('湖南 vs '+t.target, gx, padT+plotH+20);
    }
    // 图例
    ctx.textAlign='left'; ctx.font='11px "Microsoft YaHei",sans-serif';
    var lx=padL;
    for(k=0;k<g;k++){
      ctx.fillStyle=cols[k]; ctx.fillRect(lx,H-26,16,10);
      ctx.fillStyle='#cfd6e4'; ctx.fillText(lbls[k],lx+22,H-17); lx+=110;
    }
  }

  // ===== 表格 =====
  function renderTable(){
    var html='<table class="dt"><thead><tr><th>都市圈</th>';
    calibers.forEach(function(k){html+='<th>'+k+'<div class="sub">基准'+money(base[k])+'</div></th>';});
    html+='<th>区间</th><th>排序</th></tr></thead><tbody>';
    // 按非私营距离排序
    var sm=matrix.slice().sort(function(a,b){return a.vals['非私营']-b.vals['非私营'];});
    sm.forEach(function(m,idx){
      var rv=ranges.filter(function(r){return r.name===m.name;})[0];
      html+='<tr><td class="nm">'+m.name+'<div class="sub">'+m.note+'</div></td>';
      calibers.forEach(function(k){
        var v=m.vals[k];
        html+='<td class="num" style="color:'+dColor(v)+'"><b>'+pct(v)+'</b></td>';
      });
      html+='<td class="num"><span class="tag warn">'+rv.min.toFixed(1)+'% ~ '+rv.max.toFixed(1)+'%</span></td>';
      html+='<td>'+(idx+1)+'</td></tr>';
    });
    html+='</tbody></table>';
    document.getElementById('tbl').innerHTML=html;

    // vs targets 表
    var h2='<table class="dt"><thead><tr><th>对比</th><th>非私营工资</th><th>可支配收入</th><th>最低工资</th><th>解读</th></tr></thead><tbody>';
    vs_targets.forEach(function(t){
      var avg=(t['非私营']+t['可支配']+t['最低工资'])/3;
      var interp = avg<-40?'差距巨大':avg<-25?'差距显著':avg<-15?'差距明显':'差距较小';
      h2+='<tr><td class="nm">湖南 vs '+t.target+'</td>';
      ['非私营','可支配','最低工资'].forEach(function(k){
        h2+='<td class="num" style="color:'+dColor(t[k])+'"><b>'+t[k]+'%</b></td>';
      });
      h2+='<td><span class="tag '+(avg<-25?'bad':(avg<-15?'warn':'ok'))+'">'+interp+' (均值'+avg.toFixed(0)+'%)</span></td></tr>';
    });
    h2+='</tbody></table>';
    document.getElementById('tbl2').innerHTML=h2;
  }

  function init(){
    drawHeatmap(document.getElementById('c1'));
    drawRange(document.getElementById('c2'));
    drawVsTarget(document.getElementById('c3'));
    renderTable();
  }
  if(document.readyState!=='loading') init();
  else document.addEventListener('DOMContentLoaded', init);
})();
"""

# node --check
js_tmp=os.path.join(tempfile.gettempdir(),"_fdmg2_check.js")
with open(js_tmp,"w",encoding="utf-8") as f: f.write(JS_CODE)
node=r"C:\Users\wangj\.workbuddy\binaries\node\versions\22.22.2\node.exe"
try:
    r=subprocess.run([node,"--check",js_tmp],capture_output=True,text=True,timeout=30)
    js_ok=r.returncode==0; js_msg=(r.stdout+r.stderr).strip() or "OK"
except Exception as e:
    js_ok=False; js_msg=str(e)
print("[node --check]","PASS" if js_ok else "FAIL",js_msg)
if not js_ok: raise SystemExit("JS语法校验失败")

HTML="""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>地区经济治理结构差距量化 · 多口径Fdamage相对距离</title>
<style>
:root{--bg:#0e1320;--panel:#161d2e;--panel2:#1b2336;--line:#27304a;--txt:#e6e9f0;--sub:#8a93a6;--dim:#6b7488;--red:#e74c3c;--amber:#f5b942;--teal:#0d9488;--blue:#3b82f6;--green:#10b981;}
*{box-sizing:border-box;} body{margin:0;background:var(--bg);color:var(--txt);font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;}
.wrap{max-width:1180px;margin:0 auto;padding:28px 22px 60px;}
h1{font-size:25px;margin:0 0 6px;border-left:5px solid var(--teal);padding-left:14px;}
h1 small{font-size:13px;color:var(--sub);font-weight:normal;display:block;margin-top:4px;}
h2{font-size:18px;margin:30px 0 12px;color:#fff;border-bottom:1px solid var(--line);padding-bottom:8px;}
h2 .n{color:var(--teal);font-family:Consolas,monospace;margin-right:8px;}
.lead{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px 20px;margin:16px 0;color:var(--sub);font-size:14px;}
.lead b{color:var(--txt);}
.lead .formula{font-family:Consolas,monospace;background:#0c111c;padding:6px 10px;border-radius:6px;color:var(--amber);display:inline-block;margin:4px 0;}
canvas{width:100%;height:auto;background:#141a26;border:1px solid var(--line);border-radius:8px;display:block;}
.note{font-size:12px;color:var(--dim);margin-top:6px;}
table.dt{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px;background:var(--panel);border-radius:8px;overflow:hidden;}
table.dt th,table.dt td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle;}
table.dt th{background:#1a2236;color:#cfd6e4;font-weight:600;font-size:12px;}
table.dt td.num{font-family:Consolas,monospace;text-align:right;}
table.dt td.nm{font-weight:700;}
.sub{color:var(--dim);font-size:11px;font-weight:normal;}
.tag{display:inline-block;padding:2px 9px;border-radius:10px;font-size:11px;font-weight:600;}
.tag.bad{background:rgba(231,76,60,0.18);color:#ff6b5e;}
.tag.warn{background:rgba(245,185,66,0.16);color:var(--amber);}
.tag.ok{background:rgba(16,185,129,0.16);color:var(--green);}
.kpi{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0;}
.kpi .b{flex:1;min-width:170px;background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:12px 14px;}
.kpi .b .k{color:var(--sub);font-size:12px;}
.kpi .b .v{font-size:21px;font-weight:700;color:#fff;font-family:Consolas,monospace;margin-top:4px;}
.kpi .b .v.r{color:#ff6b5e;}.kpi .b .v.g{color:var(--green);}.kpi .b .v.a{color:var(--amber);}.kpi .b .v.b{color:#6ea8fe;}
.concl{background:linear-gradient(135deg,#1a2236,#161d2e);border:1px solid var(--line);border-left:4px solid var(--teal);border-radius:8px;padding:16px 20px;margin:14px 0;}
.concl h3{margin:0 0 8px;color:#fff;font-size:15px;}
.concl ol{margin:6px 0 0 18px;padding:0;color:var(--sub);}
.concl ol li{margin:5px 0;} .concl b{color:var(--txt);}
.src{font-size:11px;color:var(--dim);border-top:1px dashed var(--line);padding-top:10px;margin-top:22px;}
ul.refs{margin:6px 0 0 16px;padding:0;color:var(--dim);font-size:11px;} ul.refs li{margin:3px 0;}
</style></head><body><div class="wrap">
<h1>地区经济治理结构差距量化
<small>多口径 F<sub>damage</sub> 相对距离矩阵 —— 量化"湖南比广东/上海/成渝/首都差多远"</small>
</h1>

<div class="lead">
<b>方法论校准</b>(本轮核心调整)：
<br>① <b>F<sub>damage</sub> 的尺度性</b>：宏观层面波动小、微观层面波动大(三孩子一老娘的农民工 vs 单身汉农民工，绝望分天差地别)。地区级 F<sub>damage</sub> 是<b>治理结构层面的均值化度量</b>，压平了内部微观分化，用于回答"省际治理结构谁差、差多远"是合适的。
<br>② <b>从绝对估值转向相对距离</b>：不再求"离理论应然多远"，而是<b>以治理结构相对最优的长三角为基准=0，量化各地区相对差距</b>。
<span class="formula">距离 D<sub>i</sub> = (W<sub>i</sub> − W<sub>长三角</sub>) / W<sub>长三角</sub></span> 负值=比长三角差，负值越大差距越大。基准因对象制宜。
<br>③ <b>多口径交叉</b>：非私营单口径有系统高估(排除私营/个体/灵活就业)和区域不可比问题。本轮上四口径看"差多远"是否稳健：
A非私营 · B全口径(社保基数口径) · C全体居民人均可支配收入(含农村+转移支付，最代表治理结构对全体国民的损益) · D最低工资(生存红线L的政策实现)。
</div>

<div class="kpi">
<div class="b"><div class="k">基准·长三角非私营</div><div class="v">142,796 元</div></div>
<div class="b"><div class="k">基准·长三角可支配</div><div class="v">61,401 元</div></div>
<div class="b"><div class="k">长株潭 vs 长三角(非私)</div><div class="v r">−32.0%</div></div>
<div class="b"><div class="k">长株潭 vs 长三角(可支配)</div><div class="v r">−41.5%</div></div>
<div class="b"><div class="k">长株潭 vs 上海(非私)</div><div class="v r">−57.7%</div></div>
</div>

<h2><span class="n">壹</span>地区治理结构差距矩阵</h2>
<canvas id="c1" width="1160" height="380"></canvas>
<div class="note">每格=该口径下该都市圈相对长三角的偏离%。颜色越红差距越大。长三角自身=0(基准)。</div>

<h2><span class="n">贰</span>四口径距离区间(稳健性检验)</h2>
<canvas id="c2" width="1160" height="360"></canvas>
<div class="note">横线=该都市圈在四口径下距离长三角的范围。区间越宽说明口径越敏感。点=各口径值。</div>

<h2><span class="n">叁</span>湖南 vs 各地 差距量化</h2>
<canvas id="c3" width="1160" height="380"></canvas>
<div class="note">直接回答"湖南比广东/上海/成渝/首都差多远"。三口径交叉，均值给出综合差距。</div>

<div class="concl">
<h3>关键量化结论</h3>
<ol>
<li><b>长株潭在3/4口径下都是最差</b>(非私营−32% / 全口径−25.6% / 最低工资−17.4%)，仅可支配收入口径下略好于成渝。综合看湖南治理结构最不合理，结论稳健。</li>
<li><b>"湖南比成渝可能也差"</b>——部分成立：用工成本(非私营)湖南比成渝低13%，最低工资低8%；但全体居民可支配收入湖南反而高6%(农村收入湖南略好)。所以<b>在用工议价维度湖南更差，在居民实际所得维度成渝更差</b>。</li>
<li><b>量化"差多远"</b>：湖南 vs 广东≈−25~−27%(用工/收入)，vs 上海≈−55~−58%，vs 成渝≈−8~−13%(用工)，vs 首都(京津冀)≈−20~−22%。</li>
<li><b>长三角一骑绝尘</b>：四口径下均居首，治理结构相对最优——不是效率更高，而是结构为个体提供了对抗损价的能力(原文第4章)。</li>
<li><b>口径敏感性启示</b>：可支配收入口径差距(−20~−45%)远大于非私营(−8~−32%)，说明<b>正规部门工资掩盖了居民实际所得的更大分化</b>——这正对应"有效需求不足"是 F<sub>damage</sub> 在消费端的体现。</li>
</ol>
</div>

<h2><span class="n">肆</span>距离矩阵明细表</h2>
<div id="tbl"></div>

<h2><span class="n">伍</span>湖南 vs 各地 差距明细</h2>
<div id="tbl2"></div>

<h2><span class="n">陆</span>口径真实性与代表性说明</h2>
<div class="lead">
<b>A 非私营</b>：国有+集体+股份制+港澳台+外商，<b>排除私营和个体</b>。系统高估用工成本(正规部门工资高)，区域不可比(北京非私占比高、珠三角私营占比高)。但口径全国统一，作基准参照。<br>
<b>B 全口径</b>：非私营+私营按就业加权，社保基数官方口径，<b>真实性最好</b>。沪湘川渝为官方值，苏浙粤冀津为(非私+私)/2估算(用湘川渝官方值校验误差2-5%)。<br>
<b>C 全体居民人均可支配收入</b>：含工资+经营+财产+转移，<b>含农村</b>(农村是 F<sub>damage</sub>受损最重群体，原文第4章城乡二元)。最代表"治理结构对全体国民的损益"，对应"有效需求不足"。<br>
<b>D 最低工资首档</b>：政策定的生存红线 L 的实现，议价下限。沪京不含五险一金(含金量更高)。<br>
<b>局限</b>：①未扣地区生活成本(CPI/房价)，沪京名义高工资部分被高生活成本抵消；②平均被高管拉高，未用中位数；③长株潭用湖南省代理，核心都市区实际高于全省(会缩小与基准的差距，即实际差距可能比表中小1-3个百分点，但不改变排序)。
</div>

<div class="src">
<b>数据来源(2023年)</b>
<ul class="refs">
<li>非私营/私营年平均工资：国家统计局及各省统计局(沪229337/京218312/津138007/冀94818/苏125102/浙133045/粤131418/湘97015/川110160/渝113653)</li>
<li>全口径城镇单位社平工资：沪147684/湘80532/川90220/渝87169为官方值；苏浙粤冀津京为(非私+私)/2估算</li>
<li>全体居民人均可支配收入：国家统计局(沪84834/京81752/浙63830/苏52674/津51271/粤49327/渝37595/湘35895/川32514/冀32903)</li>
<li>最低工资标准首档：人社部截至2023-10-01(沪2690/京2420/津2180/冀2200/苏2280/浙2280/粤2300/湘1930/川2100/渝2100)</li>
<li>常住人口加权：各省2023年国民经济和社会发展统计公报</li>
</ul>
<div style="margin-top:8px">生成时间：2026-08-01 · 理论依据：王觉菊《价格损益因子理论》RC_01~07 · 多口径相对距离法</div>
</div>
</div>
<script>window.__FDATA__=__DATA__;__JS__;</script>
</body></html>"""
HTML=HTML.replace("__DATA__",data_json).replace("__JS__",JS_CODE)

out=r"Y:\jueju-portal\wangjuejudotcngen2ai\zhuzhibimo\fdamage\地区经济治理结构差距量化.html"
with open(out,"w",encoding="utf-8") as f: f.write(HTML)
print("[HTML]",out,os.path.getsize(out),"bytes")

# 控制台速览
print("\n=== 四口径距离矩阵 (vs 长三角基准=0, %) ===")
print(f"{'都市圈':8s} | "+" | ".join(f"{k:8s}" for k in CALIBERS)+" | 区间")
for i,m in enumerate(matrix):
    vals=[m["vals"][k] for k in CALIBERS]
    print(f"{m['name']:8s} | "+" | ".join(f"{v:7.1f}%" for v in vals)+f" | [{min(vals):.1f}%,{max(vals):.1f}%]")
print("\n=== 湖南 vs 各地 ===")
for t in vs_targets:
    avg=(t['非私营']+t['可支配']+t['最低工资'])/3
    print(f"  vs {t['target']:4s} 非私{t['非私营']:+6.1f}% 可支配{t['可支配']:+6.1f}% 最低工资{t['最低工资']:+6.1f}% 均值{avg:+.0f}%")
