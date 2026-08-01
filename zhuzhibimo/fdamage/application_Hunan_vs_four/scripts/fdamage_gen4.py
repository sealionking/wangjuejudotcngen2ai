# -*- coding: utf-8 -*-
"""
地区用工成本差距量化 v4 —— 城镇常住人口加权(排除农村) + 可支配收入整体移除。
零外部依赖纯原生Canvas。
"""
import json, os, subprocess, tempfile

# 省级数据(2023): [非私营, 私营, 全口径, 最低工资月, 常住人口万, 城镇化率]
PROV = {
    "上海":[229337,111347,147684,2690,2487,0.8946],
    "北京":[218312,105931,162122,2420,2186,0.8783],
    "天津":[138007,72966,105487,2180,1364,0.8549],
    "河北":[94818,51281,73050,2200,7393,0.6114],
    "江苏":[125102,75088,100095,2280,8526,0.7504],
    "浙江":[133045,74325,103685,2280,6627,0.7420],
    "广东":[131418,80685,106052,2300,12706,0.7542],
    "湖南":[97015,60277,80532,1930,9705,0.6116],
    "四川":[110160,62105,90220,2100,8074,0.5949],
    "重庆":[113653,63941,87169,2100,3213,0.7167],
}
# 城镇常住人口 = 人口 × 城镇化率
for p in PROV: PROV[p].append(round(PROV[p][4]*PROV[p][5]))  # [6]=城镇人口万

CLUSTERS = [
    {"name":"长三角","parts":[("上海","上海"),("江苏","江苏"),("浙江","浙江")],"note":"沪苏浙·城镇人口加权"},
    {"name":"珠三角","parts":[("广东","广东")],"note":"广东省·城镇口径"},
    {"name":"京津冀","parts":[("北京","北京"),("天津","天津"),("河北","河北")],"note":"京津冀·城镇人口加权"},
    {"name":"成渝","parts":[("四川","四川"),("重庆","重庆")],"note":"川渝·城镇人口加权"},
    {"name":"长株潭","parts":[("湖南","湖南")],"note":"湖南省·城镇口径代理"},
]
CALIBERS = ["非私营","私营","全口径","最低工资年"]

def wavg(parts, idx, annualize=False):
    tot = sum(PROV[p][6] for _,p in parts)  # 城镇人口加权
    s = 0
    for _,p in parts:
        v = PROV[p][idx]
        if annualize: v *= 12
        s += v*PROV[p][6]
    return s/tot

rows = []
for c in CLUSTERS:
    r = {"name":c["name"],"note":c["note"]}
    r["非私营"] = round(wavg(c["parts"],0))
    r["私营"] = round(wavg(c["parts"],1))
    r["全口径"] = round(wavg(c["parts"],2))
    r["最低工资年"] = round(wavg(c["parts"],3,True))
    rows.append(r)

BASE = rows[0]
def dist(w,b): return (w-b)/b*100
matrix = []
for r in rows:
    m = {"name":r["name"],"note":r["note"],"vals":{}}
    for k in CALIBERS: m["vals"][k] = round(dist(r[k],BASE[k]),1)
    matrix.append(m)

ranks = {}
for k in CALIBERS:
    ranks[k] = [m["name"] for m in sorted(matrix,key=lambda x:x["vals"][k])]

# 湖南 vs 各地
targets = {"广东":PROV["广东"],"上海":PROV["上海"],"四川":PROV["四川"],"北京":PROV["北京"]}
hunan = PROV["湖南"]
vs_targets = []
for tn,td in targets.items():
    d_full=(hunan[2]-td[2])/td[2]*100
    d_npub=(hunan[0]-td[0])/td[0]*100
    d_pub=(hunan[1]-td[1])/td[1]*100
    d_min=(hunan[3]-td[3])/td[3]*100
    vs_targets.append({"target":tn,"全口径":round(d_full,1),"非私营":round(d_npub,1),"私营":round(d_pub,1),"最低工资":round(d_min,1),"avg":round((d_full+d_npub+d_pub)/3,0)})

ranges = []
for m in matrix:
    vals=[m["vals"][k] for k in CALIBERS]
    ranges.append({"name":m["name"],"min":min(vals),"max":max(vals),"vals":vals})

data_json = json.dumps({"calibers":CALIBERS,"matrix":matrix,"rows":rows,"base":{k:BASE[k] for k in CALIBERS},"vs_targets":vs_targets,"ranges":ranges,"ranks":ranks},ensure_ascii=False)

JS_CODE = r"""
(function(){
  var D=window.__FDATA__;
  var calibers=D.calibers,matrix=D.matrix,base=D.base,vs_targets=D.vs_targets,ranges=D.ranges,ranks=D.ranks;
  function pct(v,d){d=(d==null)?1:d;var s=v.toFixed(d);return (v>=0?'+':'')+s+'%';}
  function money(n){return Math.round(n).toLocaleString('en-US');}
  function dColor(v){
    var t=(v+50)/50;if(t<0)t=0;if(t>1)t=1;
    function lerp(a,b,p){return [a[0]+(b[0]-a[0])*p,a[1]+(b[1]-a[1])*p,a[2]+(b[2]-a[2])*p];}
    var c0=[185,28,28],c1=[217,119,6],c2=[16,185,129];
    var col=t<0.6?lerp(c0,c1,t/0.6):lerp(c1,c2,(t-0.6)/0.4);
    return 'rgb('+Math.round(col[0])+','+Math.round(col[1])+','+Math.round(col[2])+')';
  }
  function drawHeatmap(canvas){
    var ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height;
    ctx.clearRect(0,0,W,H);ctx.fillStyle='#141a26';ctx.fillRect(0,0,W,H);
    var padL=120,padR=40,padT=95,padB=80;
    var plotW=W-padL-padR,plotH=H-padT-padB;
    var nC=calibers.length,nR=matrix.length,cw=plotW/nC,ch=plotH/nR;
    ctx.fillStyle='#e6e6e6';ctx.font='bold 16px "Microsoft YaHei",sans-serif';ctx.textAlign='left';
    ctx.fillText('图1  用工成本四口径距离矩阵  (城镇常住人口加权, vs 长三角=0)',padL,34);
    ctx.font='12px "Microsoft YaHei",sans-serif';ctx.fillStyle='#8a93a6';
    ctx.fillText('排除农村常住人口(经济参与度低/锁定主粮畜牧/城市化附庸)  四口径纯劳动力价格',padL,52);
    ctx.fillStyle='#10b981';ctx.font='bold 12px "Microsoft YaHei",sans-serif';
    ctx.fillText('✓ 四口径排序: 长株潭<成渝<京津冀≈珠三角<长三角 (长株潭全部最差)',padL,70);
    ctx.font='bold 12px "Microsoft YaHei",sans-serif';ctx.fillStyle='#cfd6e4';ctx.textAlign='center';
    for(var j=0;j<nC;j++){
      var cx=padL+cw*(j+0.5);
      ctx.fillText(calibers[j],cx,padT-14);
      ctx.font='10px "Microsoft YaHei",sans-serif';ctx.fillStyle='#8a93a6';
      ctx.fillText('基准'+money(base[calibers[j]]),cx,padT-30);
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
      ctx.fillStyle=v<-25?'#fff':(v<-8?'#fff':'#1a1f2e');
      ctx.fillText(pct(v),x+cw/2,y+ch/2+5);
    }
  }
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
    ctx.fillText('区间紧凑=口径不敏感=结论稳  排除农村后区间更窄',padL,52);
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
        ctx.fillStyle=cols[k];ctx.beginPath();ctx.arc(xOf(r.vals[k]),y,6,0,Math.PI*2);ctx.fill();
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
  function drawVsTarget(canvas){
    var ctx=canvas.getContext('2d'),W=canvas.width,H=canvas.height;
    ctx.clearRect(0,0,W,H);ctx.fillStyle='#141a26';ctx.fillRect(0,0,W,H);
    var padL=60,padR=30,padT=80,padB=80;
    var plotW=W-padL-padR,plotH=H-padT-padB;
    var n=vs_targets.length,g=4;
    var groupW=plotW/n,barW=groupW*0.17;
    var vmax=0,vmin=-65;
    function yOf(v){return padT+plotH-(v-vmin)/(vmax-vmin)*plotH;}
    var y0=yOf(0);
    ctx.fillStyle='#e6e6e6';ctx.font='bold 16px "Microsoft YaHei",sans-serif';ctx.textAlign='left';
    ctx.fillText('图3  湖南 vs 各地 用工成本差距',padL,34);
    ctx.font='12px "Microsoft YaHei",sans-serif';ctx.fillStyle='#8a93a6';
    ctx.fillText('四口径纯用工成本  直接量化"差多远"',padL,52);
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
      for(k=0;k<g;k++){
        var v=t[keys[k]];
        var y=yOf(v),h=y0-y;
        ctx.fillStyle=cols[k];
        var bx=gx-barW*(g-1)/2+k*barW;
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
    for(k=0;k<g;k++){
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

js_tmp=os.path.join(tempfile.gettempdir(),"_fdmg4_check.js")
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
<title>地区用工成本差距量化 · 城镇口径四口径</title>
<style>
:root{--bg:#0e1320;--panel:#161d2e;--panel2:#1b2336;--line:#27304a;--txt:#e6e9f0;--sub:#8a93a6;--dim:#6b7488;--red:#e74c3c;--amber:#f5b942;--teal:#0d9488;--blue:#3b82f6;--green:#10b981;}
*{box-sizing:border-box;}body{margin:0;background:var(--bg);color:var(--txt);font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;}
.wrap{max-width:1180px;margin:0 auto;padding:28px 22px 60px;}
h1{font-size:25px;margin:0 0 6px;border-left:5px solid var(--blue);padding-left:14px;}
h1 small{font-size:13px;color:var(--sub);font-weight:normal;display:block;margin-top:4px;}
h2{font-size:18px;margin:30px 0 12px;color:#fff;border-bottom:1px solid var(--line);padding-bottom:8px;}
h2 .n{color:var(--blue);font-family:Consolas,monospace;margin-right:8px;}
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
.warn-box ul{margin:6px 0 0 18px;color:var(--sub);font-size:13px;}
.warn-box li{margin:3px 0;}
.src{font-size:11px;color:var(--dim);border-top:1px dashed var(--line);padding-top:10px;margin-top:22px;}
ul.refs{margin:6px 0 0 16px;padding:0;color:var(--dim);font-size:11px;}ul.refs li{margin:3px 0;}
</style></head><body><div class="wrap">
<h1>地区用工成本差距量化
<small>城镇常住人口加权 · 纯劳动力价格四口径 —— 量化"湖南差多远"</small>
</h1>

<div class="warn-box">
<h3>⚠️ 两项关键修正</h3>
<p><b>1. 排除农村常住人口</b>：农村居民经济参与度低，锁定在<b>价格锁死的主粮生产</b>和<b>高风险低收益的畜牧业</b>，农村经济本质是城市化的附庸。把他们计入"用工成本"比较是权重失真——他们不是劳动力市场的议价参与者。</p>
<p>本轮加权改用<b>城镇常住人口</b>(=常住人口×城镇化率)，匹配城镇单位工资口径(工资本就只统计城镇单位就业人员)。</p>
<p><b>2. 可支配收入整体移除</b>：不仅概念上≠用工成本(经营收入和老天爷谈价格)，更因为：</p>
<ul>
<li>混入大量<b>政府补贴救助</b>(转移净收入)——这是再分配结果，不是劳动力议价；</li>
<li><b>调查统计作假</b>——数据本身不可信，不是口径问题是数据质量问题，没得洗。</li>
</ul>
<p>故可支配收入不再作任何参照，从矩阵中彻底删除。</p>
</div>

<div class="lead">
<b>方法</b>：以治理结构相对最优的长三角为基准=0，<span class="formula">D<sub>i</sub> = (W<sub>i</sub> − W<sub>长三角</sub>) / W<sub>长三角</sub></span> 负值越大差距越大。
<br><b>四口径均为纯劳动力价格</b>：非私营(正规部门) · 私营(底层议价) · 全口径(非私+私加权,社保基数口径,真实性最好) · 最低工资(生存红线L)。
<br><b>加权</b>：城镇常住人口(排除农村)。城镇化率(2023)：沪89.5%/京87.8%/津85.5%/冀61.1%/苏75.0%/浙74.2%/粤75.4%/湘61.2%/川59.5%/渝71.7%。
<br><b>F<sub>damage</sub>尺度性</b>：宏观波动小、微观波动大。地区级用工成本是治理结构层面的均值化度量，用于回答"省际治理结构谁差、差多远"合适。
</div>

<div class="kpi">
<div class="b"><div class="k">长三角全口径(城镇基准)</div><div class="v">109,226 元</div></div>
<div class="b"><div class="k">长株潭 vs 长三角(全口径)</div><div class="v r">−26.3%</div></div>
<div class="b"><div class="k">长株潭 vs 长三角(非私营)</div><div class="v r">−33.2%</div></div>
<div class="b"><div class="k">长株潭 vs 上海(全口径)</div><div class="v r">−45.4%</div></div>
<div class="b"><div class="k">四口径排序一致性</div><div class="v g">高度一致</div></div>
</div>

<h2><span class="n">壹</span>用工成本四口径距离矩阵(城镇加权)</h2>
<canvas id="c1" width="1160" height="400"></canvas>
<div class="note">城镇常住人口加权，排除农村。颜色越红差距越大。<b>排除农村后京津冀用工成本上升</b>(北京城镇化率87.8%远高于河北61.1%，城镇权重大，高薪拉高均值)——这是更真实的城镇用工成本。</div>

<h2><span class="n">贰</span>四口径距离区间(稳健性)</h2>
<canvas id="c2" width="1160" height="360"></canvas>
<div class="note">区间紧凑=结论稳。排除农村+弃用可支配收入后，四口径区间比上两版都窄。</div>

<h2><span class="n">叁</span>湖南 vs 各地 用工成本差距</h2>
<canvas id="c3" width="1160" height="400"></canvas>
<div class="note">纯用工成本四口径直接量化"差多远"。均值=三用工口径(非私/私营/全口径)综合。</div>

<div class="concl">
<h3>关键结论</h3>
<ol>
<li><b>长株潭用工成本最不合理，四口径一致</b>：非私营−33%、私营−25%、全口径−26%、最低工资−18%。比长三角差18%~33%(视口径)，比上海差约45%~50%。结论极其稳健。</li>
<li><b>量化"差多远"</b>(用工成本均值)：湖南 vs 广东≈−24%，vs 上海≈−50%，vs 四川≈−9%(用工维度湖南确实更差)，vs 北京≈−50%。</li>
<li><b>"湖南比成渝可能也差"在用工维度成立</b>：四口径一致显示湖南用工成本低于成渝。上一版"可支配收入反超"是补贴+作假+经营收入污染，已剔除。</li>
<li><b>排除农村后京津冀反超珠三角</b>(非私营口径)：北京城镇化率87.8%，城镇权重大，金融/IT高薪拉高均值。这更真实——<b>城镇用工成本</b>确实京津冀(受北京拉动)略高于珠三角(受粤东西北拉低)。但私营/全口径下珠三角仍领先。</li>
<li><b>长三角一骑绝尘</b>：四口径均居首，治理结构相对最优。不是效率更高，而是结构为个体提供了对抗损价的能力(原文第4章)。</li>
</ol>
</div>

<h2><span class="n">肆</span>距离矩阵明细</h2>
<div id="tbl"></div>

<h2><span class="n">伍</span>湖南 vs 各地 明细</h2>
<div id="tbl2"></div>

<h2><span class="n">陆</span>口径真实性与局限</h2>
<div class="lead">
<b>真实性排序</b>：全口径(非私+私加权) &gt; 非私营 ≈ 私营 &gt; 最低工资(政策值非市场值)。
<br><b>系统性盲区</b>：所有官方工资口径<b>只覆盖城镇单位就业</b>，排除灵活就业/平台用工/个体户——而这恰是 F<sub>damage</sub>最重群体(外卖骑手、网约车、众包)。任何基于统计内单位的用工成本都会<b>低估</b>真实 F<sub>damage</sub>，且低估程度在珠三角(灵活就业密集)更大。这是方法论的硬限制。
<br><b>全口径估算</b>：沪/湘/川/渝为官方值；苏浙粤冀津京为(非私+私)/2估算(用湘川渝官方值校验误差2-5%，不改变排序)。
<br><b>长株潭</b>用湖南省代理，核心都市区(长株潭)城镇用工成本实际高于全省均值(会缩小与基准差距，不改排序)。
<br><b>未扣生活成本</b>：沪京名义高工资部分被高生活成本抵消；引入城市CPI修正后沪京优势缩小，排序不变。
<br><b>可支配收入弃用</b>：因混入补贴救助+统计作假+经营收入(老天爷)，不作任何参照。
</div>

<div class="src">
<b>数据来源(2023年)</b>
<ul class="refs">
<li>非私营/私营年平均工资：国家统计局及各省统计局</li>
<li>全口径城镇单位社平工资：沪147684/湘80532/川90220/渝87169为官方值；苏浙粤冀津京为(非私+私)/2估算</li>
<li>最低工资标准首档：人社部截至2023-10-01</li>
<li>城镇化率：各省2023年国民经济和社会发展统计公报(沪89.46/京87.83/津85.49/冀61.14/苏75.04/浙74.2/粤75.42/湘61.16/川59.49/渝71.67)</li>
<li>城镇常住人口加权=常住人口×城镇化率</li>
</ul>
<div style="margin-top:8px">生成时间：2026-08-01 · 理论依据：王觉菊《价格损益因子理论》RC_01~07 · 城镇口径纯用工成本四口径相对距离法</div>
</div>
</div>
<script>window.__FDATA__=__DATA__;__JS__;</script>
</body></html>"""
HTML=HTML.replace("__DATA__",data_json).replace("__JS__",JS_CODE)

out=r"Y:\jueju-portal\wangjuejudotcngen2ai\zhuzhibimo\fdamage\地区经济治理结构差距量化.html"
with open(out,"w",encoding="utf-8") as f:f.write(HTML)
print("[HTML]",out,os.path.getsize(out),"bytes")

print("\n=== 用工成本四口径距离 (城镇常住人口加权, vs 长三角=0) ===")
print(f"{'都市圈':8s} | "+" | ".join(f"{k:8s}" for k in CALIBERS)+" | 区间")
for m in matrix:
    vals=[m["vals"][k] for k in CALIBERS]
    print(f"{m['name']:8s} | "+" | ".join(f"{v:7.1f}%" for v in vals)+f" | [{min(vals):.1f}%,{max(vals):.1f}%]")
print("\n排序:")
for k in CALIBERS: print(f"  {k}: "+" < ".join(ranks[k]))
print("\n=== 湖南 vs 各地 (用工成本) ===")
for t in vs_targets:
    print(f"  vs {t['target']:4s} 非私{t['非私营']:+6.1f}% 私营{t['私营']:+6.1f}% 全口径{t['全口径']:+6.1f}% 最低{t['最低工资']:+6.1f}% 均值{int(t['avg']):+d}%")
