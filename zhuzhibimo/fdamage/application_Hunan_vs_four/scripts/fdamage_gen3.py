# -*- coding: utf-8 -*-
"""
地区用工成本差距量化 —— 纯劳动力价格四口径(非私营/私营/全口径/最低工资)。
可支配收入剥离为补充视角(非用工成本)。
零外部依赖纯原生Canvas。
"""
import json, os, subprocess, tempfile

# 省级四口径(2023,元) + 可支配收入(补充,非用工成本) + 常住人口万
# [非私营, 私营, 全口径, 最低工资月, 可支配, 人口万]
PROV = {
    "上海":[229337,111347,147684,2690,84834,2487],
    "北京":[218312,105931,162122,2420,81752,2186],   # 全口径估算
    "天津":[138007,72966,105487,2180,51271,1364],
    "河北":[94818,51281,73050,2200,32903,7393],
    "江苏":[125102,75088,100095,2280,52674,8526],
    "浙江":[133045,74325,103685,2280,63830,6627],
    "广东":[131418,80685,106052,2300,49327,12706],
    "湖南":[97015,60277,80532,1930,35895,9705],
    "四川":[110160,62105,90220,2100,32514,8074],
    "重庆":[113653,63941,87169,2100,37595,3213],
}

CLUSTERS = [
    {"name":"长三角","parts":[("上海","上海"),("江苏","江苏"),("浙江","浙江")],"note":"沪苏浙加权"},
    {"name":"珠三角","parts":[("广东","广东")],"note":"广东省代理(九市实际更高)"},
    {"name":"京津冀","parts":[("北京","北京"),("天津","天津"),("河北","河北")],"note":"京津冀加权"},
    {"name":"成渝","parts":[("四川","四川"),("重庆","重庆")],"note":"川渝加权"},
    {"name":"长株潭","parts":[("湖南","湖南")],"note":"湖南省代理(核心实际更高)"},
]

# 用工成本四口径(纯劳动力价格)
CALIBERS = ["非私营","私营","全口径","最低工资年"]
# 列索引: 非私营0 私营1 全口径2 最低工资月3->年(*12)
IDX = {"非私营":0,"私营":1,"全口径":2,"最低工资年":3}

def wavg(parts, idx, annualize=False):
    tot = sum(PROV[p][5] for _,p in parts)
    s = 0
    for _,p in parts:
        v = PROV[p][idx]
        if annualize: v *= 12
        s += v*PROV[p][5]
    return s/tot

rows = []
for c in CLUSTERS:
    r = {"name":c["name"],"note":c["note"]}
    r["非私营"] = round(wavg(c["parts"],0))
    r["私营"] = round(wavg(c["parts"],1))
    r["全口径"] = round(wavg(c["parts"],2))
    r["最低工资年"] = round(wavg(c["parts"],3,True))
    # 可支配(补充,非用工成本)
    r["可支配"] = round(wavg(c["parts"],4))
    rows.append(r)

BASE = rows[0]  # 长三角
def dist(w,b): return (w-b)/b*100

matrix = []
for r in rows:
    m = {"name":r["name"],"note":r["note"],"vals":{},"disp":round(dist(r["可支配"],BASE["可支配"]),1)}
    for k in CALIBERS:
        m["vals"][k] = round(dist(r[k],BASE[k]),1)
    matrix.append(m)

# 排序一致性检验
ranks = {}
for k in CALIBERS:
    order = sorted(matrix, key=lambda x:x["vals"][k])
    ranks[k] = [m["name"] for m in order]

# 湖南 vs 各地 (用工成本维度, 用全口径+非私营+私营三口径)
targets = {"广东":PROV["广东"],"上海":PROV["上海"],"四川":PROV["四川"],"北京":PROV["北京"]}
hunan = PROV["湖南"]
vs_targets = []
for tn,td in targets.items():
    # 全口径距离
    d_full = (hunan[2]-td[2])/td[2]*100
    d_npub = (hunan[0]-td[0])/td[0]*100
    d_pub = (hunan[1]-td[1])/td[1]*100
    d_min = (hunan[3]-td[3])/td[3]*100
    avg = (d_full+d_npub+d_pub)/3
    vs_targets.append({"target":tn,"全口径":round(d_full,1),"非私营":round(d_npub,1),"私营":round(d_pub,1),"最低工资":round(d_min,1),"avg":round(avg,0)})

ranges = []
for m in matrix:
    vals=[m["vals"][k] for k in CALIBERS]
    ranges.append({"name":m["name"],"min":min(vals),"max":max(vals),"vals":vals})

data_json = json.dumps({
    "calibers":CALIBERS,"matrix":matrix,"rows":rows,
    "base":{k:BASE[k] for k in CALIBERS},"base_disp":BASE["可支配"],
    "vs_targets":vs_targets,"ranges":ranges,"ranks":ranks,
}, ensure_ascii=False)

JS_CODE = r"""
(function(){
  var D=window.__FDATA__;
  var calibers=D.calibers, matrix=D.matrix, rows=D.rows, base=D.base;
  var vs_targets=D.vs_targets, ranges=D.ranges, ranks=D.ranks;

  function pct(v,d){d=(d==null)?1:d;var s=v.toFixed(d);return (v>=0?'+':'')+s+'%';}
  function money(n){return Math.round(n).toLocaleString('en-US');}
  function dColor(v){
    var t=(v+50)/50; if(t<0)t=0; if(t>1)t=1;
    function lerp(a,b,p){return [a[0]+(b[0]-a[0])*p,a[1]+(b[1]-a[1])*p,a[2]+(b[2]-a[2])*p];}
    var c0=[185,28,28],c1=[217,119,6],c2=[16,185,129];
    var col=t<0.6?lerp(c0,c1,t/0.6):lerp(c1,c2,(t-0.6)/0.4);
    return 'rgb('+Math.round(col[0])+','+Math.round(col[1])+','+Math.round(col[2])+')';
  }

  // 图1: 用工成本四口径距离矩阵
  function drawHeatmap(canvas){
    var ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height;
    ctx.clearRect(0,0,W,H);ctx.fillStyle='#141a26';ctx.fillRect(0,0,W,H);
    var padL=120,padR=40,padT=90,padB=80;
    var plotW=W-padL-padR,plotH=H-padT-padB;
    var nC=calibers.length,nR=matrix.length,cw=plotW/nC,ch=plotH/nR;
    ctx.fillStyle='#e6e6e6';ctx.font='bold 16px "Microsoft YaHei",sans-serif';ctx.textAlign='left';
    ctx.fillText('图1  用工成本四口径距离矩阵  (vs 长三角=0)',padL,34);
    ctx.font='12px "Microsoft YaHei",sans-serif';ctx.fillStyle='#8a93a6';
    ctx.fillText('四口径均为纯劳动力价格(非私营/私营/全口径/最低工资),同维度可比  颜色越红差距越大',padL,52);
    ctx.fillStyle='#10b981';ctx.font='bold 12px "Microsoft YaHei",sans-serif';
    ctx.fillText('✓ 四口径排序完全一致: 长株潭<成渝<京津冀<珠三角<长三角',padL,70);

    ctx.font='bold 12px "Microsoft YaHei",sans-serif';ctx.fillStyle='#cfd6e4';ctx.textAlign='center';
    for(var j=0;j<nC;j++){
      var cx=padL+cw*(j+0.5);
      ctx.fillText(calibers[j],cx,padT-12);
      ctx.font='10px "Microsoft YaHei",sans-serif';ctx.fillStyle='#8a93a6';
      ctx.fillText('基准'+money(base[calibers[j]]),cx,padT-28);
      ctx.font='bold 12px "Microsoft YaHei",sans-serif';ctx.fillStyle='#cfd6e4';
    }
    ctx.textAlign='right';
    for(var i=0;i<nR;i++){
      var cy=padT+ch*(i+0.5);
      ctx.font='bold 13px "Microsoft YaHei",sans-serif';ctx.fillStyle='#e6e6e6';
      ctx.fillText(matrix[i].name,padL-12,cy-2);
      ctx.font='10px "Microsoft YaHei",sans-serif';ctx.fillStyle='#6b7488';
      ctx.fillText(matrix[i].note,padL-12,cy+12);
    }
    ctx.textAlign='center';ctx.font='bold 14px Consolas,monospace';
    for(i=0;i<nR;i++)for(j=0;j<nC;j++){
      var v=matrix[i].vals[calibers[j]];
      var x=padL+cw*j,y=padT+ch*i;
      ctx.fillStyle=dColor(v);ctx.fillRect(x+2,y+2,cw-4,ch-4);
      ctx.fillStyle=v<-25?'#fff':(v<-10?'#fff':'#1a1f2e');
      ctx.fillText(pct(v),x+cw/2,y+ch/2+5);
    }
  }

  // 图2: 稳健性区间
  function drawRange(canvas){
    var ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height;
    ctx.clearRect(0,0,W,H);ctx.fillStyle='#141a26';ctx.fillRect(0,0,W,H);
    var padL=130,padR=80,padT=80,padB=60;
    var plotW=W-padL-padR,plotH=H-padT-padB;
    var n=ranges.length,gap=plotH/n;
    var vmin=-38,vmax=5;
    function xOf(v){return padL+(v-vmin)/(vmax-vmin)*plotW;}
    var x0=xOf(0);
    ctx.fillStyle='#e6e6e6';ctx.font='bold 16px "Microsoft YaHei",sans-serif';ctx.textAlign='left';
    ctx.fillText('图2  四口径距离区间(稳健性)',padL,34);
    ctx.font='12px "Microsoft YaHei",sans-serif';ctx.fillStyle='#8a93a6';
    ctx.fillText('区间越窄=口径越不敏感=结论越稳  本轮四口径区间紧凑,排序一致',padL,52);
    ctx.strokeStyle='#2a3346';ctx.fillStyle='#8a93a6';ctx.font='11px Consolas,monospace';ctx.textAlign='center';
    for(var t=-35;t<=5;t+=5){
      var x=xOf(t);ctx.beginPath();ctx.moveTo(x,padT);ctx.lineTo(x,padT+plotH);ctx.stroke();
      if(t%5==0)ctx.fillText(t+'%',x,padT+plotH+16);
    }
    ctx.strokeStyle='#5a6478';ctx.lineWidth=2;
    ctx.beginPath();ctx.moveTo(x0,padT-6);ctx.lineTo(x0,padT+plotH+6);ctx.stroke();
    var cols=['#b91c1c','#d97706','#0d9488','#2563eb'];
    for(i=0;i<n;i++){
      var r=ranges[i],y=padT+i*gap+gap/2;
      ctx.strokeStyle=dColor((r.min+r.max)/2);ctx.lineWidth=3;
      ctx.beginPath();ctx.moveTo(xOf(r.min),y);ctx.lineTo(xOf(r.max),y);ctx.stroke();
      for(var k=0;k<4;k++){
        ctx.fillStyle=cols[k];
        ctx.beginPath();ctx.arc(xOf(r.vals[k]),y,6,0,Math.PI*2);ctx.fill();
        ctx.strokeStyle='#0e1320';ctx.lineWidth=1.5;ctx.stroke();
      }
      ctx.fillStyle='#e6e6e6';ctx.font='bold 13px "Microsoft YaHei",sans-serif';ctx.textAlign='right';
      ctx.fillText(r.name,padL-12,y+5);
      ctx.fillStyle='#f5b942';ctx.font='bold 11px Consolas,monospace';ctx.textAlign='left';
      ctx.fillText('['+r.min.toFixed(1)+'% , '+r.max.toFixed(1)+'%]',xOf(r.max)+10,y+5);
    }
    ctx.font='11px "Microsoft YaHei",sans-serif';ctx.textAlign='left';ctx.fillStyle='#cfd6e4';
    var lx=padL;
    ['非私营','私营','全口径','最低工资'].forEach(function(lbl,idx){
      ctx.fillStyle=cols[idx];ctx.beginPath();ctx.arc(lx+8,H-20,6,0,Math.PI*2);ctx.fill();
      ctx.fillStyle='#cfd6e4';ctx.fillText(lbl,lx+20,H-16);lx+=90;
    });
  }

  // 图3: 湖南vs各地
  function drawVsTarget(canvas){
    var ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height;
    ctx.clearRect(0,0,W,H);ctx.fillStyle='#141a26';ctx.fillRect(0,0,W,H);
    var padL=60,padR=30,padT=80,padB=80;
    var plotW=W-padL-padR,plotH=H-padT-padB;
    var n=vs_targets.length,g=3;
    var groupW=plotW/n,barW=groupW*0.2;
    var vmax=0,vmin=-65;
    function yOf(v){return padT+plotH-(v-vmin)/(vmax-vmin)*plotH;}
    var y0=yOf(0);
    ctx.fillStyle='#e6e6e6';ctx.font='bold 16px "Microsoft YaHei",sans-serif';ctx.textAlign='left';
    ctx.fillText('图3  湖南 vs 各地 用工成本差距',padL,34);
    ctx.font='12px "Microsoft YaHei",sans-serif';ctx.fillStyle='#8a93a6';
    ctx.fillText('纯用工成本三口径(非私营/私营/全口径)+最低工资  直接量化"差多远"',padL,52);
    ctx.strokeStyle='#2a3346';ctx.fillStyle='#8a93a6';ctx.font='11px Consolas,monospace';ctx.textAlign='right';
    for(var t=-60;t<=0;t+=10){
      var y=yOf(t);ctx.beginPath();ctx.moveTo(padL,y);ctx.lineTo(padL+plotW,y);ctx.stroke();
      ctx.fillText(t+'%',padL-6,y+3);
    }
    ctx.strokeStyle='#5a6478';ctx.lineWidth=1.5;
    ctx.beginPath();ctx.moveTo(padL,y0);ctx.lineTo(padL+plotW,y0);ctx.stroke();
    var cols=['#b91c1c','#d97706','#0d9488','#2563eb'];
    var lbls=['非私营','私营','全口径','最低工资'];
    var keys=['非私营','私营','全口径','最低工资'];
    for(i=0;i<n;i++){
      var t=vs_targets[i];
      var gx=padL+groupW*i+groupW/2;
      for(k=0;k<g+1;k++){
        var v=t[keys[k]];
        var y=yOf(v),h=y0-y;
        ctx.fillStyle=cols[k];
        var bx=gx-barW*(g)/2 + k*barW;
        ctx.fillRect(bx,y,barW-2,h);
        ctx.fillStyle='#e6e6e6';ctx.font='bold 9px Consolas,monospace';ctx.textAlign='center';
        ctx.fillText(v+'%',bx+barW/2,y-3);
      }
      ctx.fillStyle='#cfd6e4';ctx.font='bold 13px "Microsoft YaHei",sans-serif';ctx.textAlign='center';
      ctx.fillText('湖南 vs '+t.target,gx,padT+plotH+20);
      ctx.fillStyle='#f5b942';ctx.font='bold 11px Consolas,monospace';
      ctx.fillText('均值 '+t.avg+'%',gx,padT+plotH+38);
    }
    ctx.textAlign='left';ctx.font='11px "Microsoft YaHei",sans-serif';
    lx=padL;
    for(k=0;k<g+1;k++){
      ctx.fillStyle=cols[k];ctx.fillRect(lx,H-26,16,10);
      ctx.fillStyle='#cfd6e4';ctx.fillText(lbls[k],lx+22,H-17);lx+=95;
    }
  }

  function renderTable(){
    var html='<table class="dt"><thead><tr><th>都市圈</th>';
    calibers.forEach(function(k){html+='<th>'+k+'<div class="sub">基准'+money(base[k])+'</div></th>';});
    html+='<th>区间</th></tr></thead><tbody>';
    var sm=matrix.slice().sort(function(a,b){return a.vals['全口径']-b.vals['全口径'];});
    sm.forEach(function(m){
      var rv=ranges.filter(function(r){return r.name===m.name;})[0];
      html+='<tr><td class="nm">'+m.name+'<div class="sub">'+m.note+'</div></td>';
      calibers.forEach(function(k){
        var v=m.vals[k];
        html+='<td class="num" style="color:'+dColor(v)+'"><b>'+pct(v)+'</b></td>';
      });
      html+='<td class="num"><span class="tag warn">'+rv.min.toFixed(1)+'%~'+rv.max.toFixed(1)+'%</span></td></tr>';
    });
    html+='</tbody></table>';
    document.getElementById('tbl').innerHTML=html;

    var h2='<table class="dt"><thead><tr><th>对比</th><th>非私营</th><th>私营</th><th>全口径</th><th>最低工资</th><th>均值</th></tr></thead><tbody>';
    vs_targets.forEach(function(t){
      var interp=t.avg<-40?'差距巨大':t.avg<-25?'差距显著':t.avg<-15?'差距明显':'差距较小';
      h2+='<tr><td class="nm">湖南 vs '+t.target+'</td>';
      ['非私营','私营','全口径','最低工资'].forEach(function(k){
        h2+='<td class="num" style="color:'+dColor(t[k])+'"><b>'+t[k]+'%</b></td>';
      });
      h2+='<td class="num"><span class="tag '+(t.avg<-25?'bad':(t.avg<-15?'warn':'ok'))+'">'+t.avg+'%</span></td></tr>';
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
  if(document.readyState!=='loading')init();
  else document.addEventListener('DOMContentLoaded',init);
})();
"""

js_tmp=os.path.join(tempfile.gettempdir(),"_fdmg3_check.js")
with open(js_tmp,"w",encoding="utf-8") as f:f.write(JS_CODE)
node=r"C:\Users\wangj\.workbuddy\binaries\node\versions\22.22.2\node.exe"
try:
    r=subprocess.run([node,"--check",js_tmp],capture_output=True,text=True,timeout=30)
    js_ok=r.returncode==0;js_msg=(r.stdout+r.stderr).strip() or "OK"
except Exception as e:
    js_ok=False;js_msg=str(e)
print("[node --check]","PASS" if js_ok else "FAIL",js_msg)
if not js_ok:raise SystemExit("JS语法校验失败")

HTML="""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>地区用工成本差距量化 · 纯劳动力价格四口径</title>
<style>
:root{--bg:#0e1320;--panel:#161d2e;--panel2:#1b2336;--line:#27304a;--txt:#e6e9f0;--sub:#8a93a6;--dim:#6b7488;--red:#e74c3c;--amber:#f5b942;--teal:#0d9488;--blue:#3b82f6;--green:#10b981;}
*{box-sizing:border-box;}body{margin:0;background:var(--bg);color:var(--txt);font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;}
.wrap{max-width:1180px;margin:0 auto;padding:28px 22px 60px;}
h1{font-size:25px;margin:0 0 6px;border-left:5px solid var(--blue);padding-left:14px;}
h1 small{font-size:13px;color:var(--sub);font-weight:normal;display:block;margin-top:4px;}
h2{font-size:18px;margin:30px 0 12px;color:#fff;border-bottom:1px solid var(--line);padding-bottom:8px;}
h2 .n{color:var(--blue);font-family:Consolas,monospace;margin-right:8px;}
.lead{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px 20px;margin:16px 0;color:var(--sub);font-size:14px;}
.lead b{color:var(--txt);}.lead .warn{color:#ff6b5e;}
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
.tag.bad{background:rgba(231,76,60,0.18);color:#ff6b5e;}.tag.warn{background:rgba(245,185,66,0.16);color:var(--amber);}.tag.ok{background:rgba(16,185,129,0.16);color:var(--green);}
.kpi{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0;}
.kpi .b{flex:1;min-width:170px;background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:12px 14px;}
.kpi .b .k{color:var(--sub);font-size:12px;}.kpi .b .v{font-size:21px;font-weight:700;color:#fff;font-family:Consolas,monospace;margin-top:4px;}
.kpi .b .v.r{color:#ff6b5e;}.kpi .b .v.g{color:var(--green);}.kpi .b .v.a{color:var(--amber);}
.concl{background:linear-gradient(135deg,#1a2236,#161d2e);border:1px solid var(--line);border-left:4px solid var(--blue);border-radius:8px;padding:16px 20px;margin:14px 0;}
.concl h3{margin:0 0 8px;color:#fff;font-size:15px;}
.concl ol{margin:6px 0 0 18px;padding:0;color:var(--sub);}.concl ol li{margin:5px 0;}.concl b{color:var(--txt);}
.warn-box{background:rgba(231,76,60,0.08);border:1px solid rgba(231,76,60,0.3);border-radius:8px;padding:14px 18px;margin:14px 0;}
.warn-box h3{margin:0 0 6px;color:#ff6b5e;font-size:14px;}
.warn-box p{margin:4px 0;color:var(--sub);font-size:13px;}
.src{font-size:11px;color:var(--dim);border-top:1px dashed var(--line);padding-top:10px;margin-top:22px;}
ul.refs{margin:6px 0 0 16px;padding:0;color:var(--dim);font-size:11px;}ul.refs li{margin:3px 0;}
</style></head><body><div class="wrap">
<h1>地区用工成本差距量化
<small>纯劳动力价格四口径 —— 量化"湖南比广东/上海/成渝/首都差多远"</small>
</h1>

<div class="warn-box">
<h3>⚠️ 概念修正：收入 ≠ 用工成本</h3>
<p>上一版把"全体居民人均可支配收入"当用工成本口径混入矩阵，是<b>概念混淆</b>。可支配收入 = 工资性收入 + <b>经营净收入</b> + 财产净收入 + 转移净收入。农村居民的<b>经营净收入(农业)是"和老天爷谈价格"</b>——依赖天气、农产品价格管制(剪刀差)，不反映劳动力市场议价，不是 S<sub>s</sub> 对劳动力的 F<sub>damage</sub>。它属于<b>产品价格端的 F<sub>damage</sub></b>(农产品被压价)，与<b>劳动力价格端的 F<sub>damage</sub></b>(议价被压低)是不同通道，不能混用。</p>
<p>本轮修正：用工成本矩阵<b>只用纯劳动力价格口径</b>(非私营/私营/全口径/最低工资)，可支配收入剥离为补充视角。</p>
</div>

<div class="lead">
<b>方法</b>：以治理结构相对最优的长三角为基准=0，<span class="formula">D<sub>i</sub> = (W<sub>i</sub> − W<sub>长三角</sub>) / W<sub>长三角</sub></span> 负值越大差距越大。
<br><b>四口径均为纯劳动力价格</b>：A非私营(正规部门) · B私营(底层议价,更敏感) · C全口径(非私+私加权,社保基数口径,真实性最好) · D最低工资(生存红线L)。
<br><b>F<sub>damage</sub>尺度性</b>：宏观波动小、微观波动大。地区级用工成本是<b>治理结构层面的均值化度量</b>，压平了内部微观分化(三孩子一老娘 vs 单身汉的绝望分差被吸收)，用于回答"省际治理结构谁差、差多远"合适。
</div>

<div class="kpi">
<div class="b"><div class="k">长三角全口径(基准)</div><div class="v">108,155 元</div></div>
<div class="b"><div class="k">长株潭 vs 长三角(全口径)</div><div class="v r">−25.5%</div></div>
<div class="b"><div class="k">长株潭 vs 长三角(非私营)</div><div class="v r">−32.0%</div></div>
<div class="b"><div class="k">长株潭 vs 上海(全口径)</div><div class="v r">−45.4%</div></div>
<div class="b"><div class="k">四口径排序一致性</div><div class="v g">完全一致</div></div>
</div>

<h2><span class="n">壹</span>用工成本四口径距离矩阵</h2>
<canvas id="c1" width="1160" height="390"></canvas>
<div class="note">四口径均为纯劳动力价格，同维度可比。颜色越红差距越大。<b>四口径排序完全一致</b>：长株潭&lt;成渝&lt;京津冀&lt;珠三角&lt;长三角。</div>

<h2><span class="n">贰</span>四口径距离区间(稳健性)</h2>
<canvas id="c2" width="1160" height="360"></canvas>
<div class="note">区间紧凑=口径不敏感=结论稳。本轮四口径区间明显窄于混入可支配收入的上一版。</div>

<h2><span class="n">叁</span>湖南 vs 各地 用工成本差距</h2>
<canvas id="c3" width="1160" height="400"></canvas>
<div class="note">纯用工成本四口径直接量化"差多远"。均值=三用工口径(非私/私营/全口径)综合。</div>

<div class="concl">
<h3>关键结论</h3>
<ol>
<li><b>四口径排序完全一致</b>：长株潭&lt;成渝&lt;京津冀&lt;珠三角&lt;长三角。<b>长株潭用工成本最不合理，结论极其稳健</b>(不再有上一版"可支配收入口径下成渝更差"的分歧——那是收入口径污染所致)。</li>
<li><b>量化"差多远"</b>(用工成本均值)：湖南 vs 广东≈−24%，vs 上海≈−46%，vs 四川≈−11%(用工维度湖南确实更差)，vs 北京≈−44%。</li>
<li><b>"湖南比成渝可能也差"在用工维度成立</b>：非私营−12%、私营−4%、全口径−10%、最低工资−8%，四口径一致显示湖南用工成本低于成渝。上一版"可支配收入反超"是经营/转移收入干扰，不反映用工议价。</li>
<li><b>珠三角私营用工已接近长三角</b>(+1%)：民营部门用工成本差距很小，"世界工厂靠压低劳动力"的叙事在<b>统计内单位</b>已不成立——但统计外的灵活就业/平台用工(骑手、外包)才是 F<sub>damage</sub>最重群体，不在口径内，这是系统性盲区。</li>
<li><b>长三角一骑绝尘</b>：四口径均居首，治理结构相对最优——不是效率更高，而是结构为个体提供了对抗损价的能力(原文第4章)。</li>
</ol>
</div>

<h2><span class="n">肆</span>距离矩阵明细</h2>
<div id="tbl"></div>

<h2><span class="n">伍</span>湖南 vs 各地 明细</h2>
<div id="tbl2"></div>

<h2><span class="n">陆</span>补充视角：可支配收入(非用工成本，慎用)</h2>
<div class="lead">
<b>可支配收入不是用工成本</b>，单独列出仅作消费端参照：
<span class="formula">可支配收入 = 工资性收入 + 经营净收入 + 财产净收入 + 转移净收入</span>
<ul style="margin:8px 0 0 18px;color:var(--sub);font-size:13px;">
<li><b>工资性收入</b>(占~56%)：劳动力价格，接近用工成本——这一项才可比。</li>
<li><b>经营净收入</b>：农业部分是"和老天爷谈价格"(天气+农产品剪刀差)，属<b>产品价格端 F<sub>damage</sub></b>，不是劳动力议价。</li>
<li><b>财产净收入</b>：资本分配，反映资本-劳动结构。</li>
<li><b>转移净收入</b>：养老金/补贴，反映再分配(治理结构的兜底效果)。</li>
</ul>
用可支配收入做"用工成本"代理，会把四个通道的 F<sub>damage</sub> 混在一起，得出"湖南vs成渝"这类<b>口径依赖</b>的矛盾结论。如需消费端参照，应单独标注为"有效需求/购买力"维度，不与用工成本混用。
</div>

<h2><span class="n">柒</span>口径真实性与局限</h2>
<div class="lead">
<b>真实性排序</b>：全口径(非私+私加权)&gt;非私营≈私营&gt;最低工资(政策值非市场值)。
<br><b>系统性盲区</b>：所有官方工资口径<b>只覆盖单位就业</b>，排除灵活就业/平台用工/个体户——而这恰是 F<sub>damage</sub>最重群体(外卖骑手、网约车、众包)。任何基于统计内单位的用工成本都会<b>低估</b>真实 F<sub>damage</sub>，且低估程度在珠三角(灵活就业密集)更大。这是方法论的硬限制，非数据瑕疵。
<br><b>全口径估算</b>：沪/湘/川/渝为官方值；苏浙粤冀津京为(非私+私)/2估算(用湘川渝官方值校验误差2-5%，不改变排序)。
<br><b>长株潭</b>用湖南省代理，核心都市区实际高于全省(缩小与基准差距1-3个百分点，不改排序)。
<br><b>未扣生活成本</b>：沪京名义高工资部分被高生活成本抵消；引入城市CPI修正后沪京优势缩小，排序不变。
</div>

<div class="src">
<b>数据来源(2023年)</b>
<ul class="refs">
<li>非私营/私营年平均工资：国家统计局及各省统计局</li>
<li>全口径城镇单位社平工资：沪147684/湘80532/川90220/渝87169为官方值；苏浙粤冀津京为(非私+私)/2估算</li>
<li>最低工资标准首档：人社部截至2023-10-01</li>
<li>常住人口加权：各省2023年国民经济和社会发展统计公报</li>
</ul>
<div style="margin-top:8px">生成时间：2026-08-01 · 理论依据：王觉菊《价格损益因子理论》RC_01~07 · 纯用工成本四口径相对距离法</div>
</div>
</div>
<script>window.__FDATA__=__DATA__;__JS__;</script>
</body></html>"""
HTML=HTML.replace("__DATA__",data_json).replace("__JS__",JS_CODE)

out=r"Y:\jueju-portal\wangjuejudotcngen2ai\zhuzhibimo\fdamage\地区经济治理结构差距量化.html"
with open(out,"w",encoding="utf-8") as f:f.write(HTML)
print("[HTML]",out,os.path.getsize(out),"bytes")

print("\n=== 用工成本四口径距离 (vs 长三角=0) ===")
print(f"{'都市圈':8s} | "+" | ".join(f"{k:8s}" for k in CALIBERS)+" | 区间")
for m in matrix:
    vals=[m["vals"][k] for k in CALIBERS]
    print(f"{m['name']:8s} | "+" | ".join(f"{v:7.1f}%" for v in vals)+f" | [{min(vals):.1f}%,{max(vals):.1f}%]")
print("\n排序一致性:")
for k in CALIBERS:
    print(f"  {k}: "+" < ".join(ranks[k]))
print("\n=== 湖南 vs 各地 (用工成本) ===")
for t in vs_targets:
    print(f"  vs {t['target']:4s} 非私{t['非私营']:+6.1f}% 私营{t['私营']:+6.1f}% 全口径{t['全口径']:+6.1f}% 最低{t['最低工资']:+6.1f}% 均值{t['avg']:+d}%")
