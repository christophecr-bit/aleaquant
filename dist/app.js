const $ = (s) => document.querySelector(s);
const pairs = [];
for(let a=1;a<=6;a++) for(let b=a+1;b<=6;b++) pairs.push([a,b]);
function selectSum(value){
  const sum=Number(value);
  if(![3,5,7,9,11].includes(sum)) throw new Error("Somme proposée : 3, 5, 7, 9 ou 11.");
  $("#sum-select").value=String(sum);
  const selected=pairs.filter(([a,b])=>a+b===sum);
  $("#fraction").textContent=selected.length+" / "+pairs.length;
  $("#pairs").textContent=selected.map(([a,b])=>a+" + "+b).join(" · ");
  $("#chart").replaceChildren(...Array.from({length:9},(_,i)=>{
    const n=i+3,count=pairs.filter(([a,b])=>a+b===n).length;
    const bar=document.createElement("div");bar.className="bar"+(n===sum?" active":"");bar.style.height=(count*60)+"px";
    const label=document.createElement("span");label.textContent=n;const number=document.createElement("b");number.textContent=count;bar.append(label,number);return bar;
  }));
  return {sum,count:selected.length,total:pairs.length,pairs:selected};
}
$("#sum-select").addEventListener("change",e=>selectSum(e.target.value));selectSum(7);
let features=[],filter="all";
const normalize=s=>s.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
function renderMetrics(){
 const query=normalize($("#metric-search").value);
 const visible=features.filter(f=>(filter==="all"||f.group===filter)&&normalize(f.name+" "+f.definition+" "+f.id).includes(query));
 $("#metric-count").textContent=visible.length+" / "+features.length+" définitions";
 $("#metrics").replaceChildren(...visible.map(f=>{
  const item=document.createElement("details");item.className="metric";
  const title=document.createElement("summary");const tag=document.createElement("small");tag.textContent=f.group==="main"?"NUMÉROS":"ÉTOILES";title.append(tag,document.createTextNode(f.name));
  const body=document.createElement("p");body.textContent=f.definition;const code=document.createElement("code");code.textContent=f.id;item.append(title,body,code);return item;
 }));
 if(!visible.length) {const p=document.createElement("p");p.className="notice";p.textContent="Aucune métrique ne correspond à cette recherche.";$("#metrics").append(p);}
}
$("#metric-search").addEventListener("input",renderMetrics);
document.querySelectorAll("[data-filter]").forEach(b=>b.addEventListener("click",()=>{filter=b.dataset.filter;document.querySelectorAll("[data-filter]").forEach(x=>x.setAttribute("aria-pressed",String(x===b)));renderMetrics();}));
fetch("metrics.json").then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{features=data;renderMetrics();}).catch(()=>{$("#metrics").textContent="Le dictionnaire n’a pas pu être chargé. Réessaie en actualisant la page.";});
function readArticle(article){
 const reader=$("#article-reader");reader.replaceChildren();reader.hidden=false;reader.className="article-reader";
 const title=document.createElement("h2");title.textContent=article.draft.title;title.tabIndex=-1;
 const status=document.createElement("p");status.className="small";status.textContent="Relu et approuvé · "+article.human_decision.reviewer;
 const prose=document.createElement("div");prose.className="prose";prose.textContent=article.draft.body;
 // Puces de rareté : calculées côté moteur (draft.badges), une seule par mesure au-dessus
 // de sa propre référence. Rendu en textContent exclusivement : le corps de l'article
 // vient d'un LLM, aucune insertion de HTML n'est faite ici, ni ailleurs.
 const badges=Array.isArray(article.draft.badges)?article.draft.badges:[];
 let chips=null;
 if(badges.length){
  chips=document.createElement("p");chips.className="article-badges";
  const intro=document.createElement("span");intro.className="small";intro.textContent="Mesures au-dessus de leur niveau habituel :";chips.append(intro);
  badges.forEach(b=>{
   const niveau=["COMMON","UNCOMMON","RARE","VERY_RARE"].includes(b.niveau)?b.niveau:"COMMON";
   const chip=document.createElement("span");chip.className="chip "+niveau;
   chip.textContent=String(b.nom)+" "+String(b.valeur)+" · "+String(b.libelle);
   chip.title=String(b.libelle)+" — seuls "+(100*Number(b.part_au_dessus)).toFixed(1)+" % des tirages dépassent le niveau habituel de cette mesure";
   chips.append(chip);
  });
 }
 const proof=document.createElement("details");const summary=document.createElement("summary");summary.textContent="Voir les preuves et la traçabilité";proof.append(summary);
 const list=document.createElement("ol");article.research_pack.evidence.forEach(e=>{const li=document.createElement("li");li.textContent="["+e.evidence_id+"] "+e.claim+" — "+e.method;list.append(li);});proof.append(list);
 const hash=document.createElement("code");hash.textContent="Version approuvée : "+article.draft_sha256;proof.append(hash);
 reader.append(status,title);if(chips)reader.append(chips);reader.append(prose);
 // AleaQuant · 2026-10-02 · v1 : projection publique liée au SHA approuvé.
 const method=article.draft.methodology;
 if(method){
  const section=document.createElement("section");const h=document.createElement("h3");h.textContent="Sources et méthode";section.append(h);
  String(method.note).split("\n\n").forEach(t=>{const p=document.createElement("p");p.textContent=t;section.append(p);});
  const details=document.createElement("details");const heading=document.createElement("summary");heading.textContent="Sources et calculs";details.append(heading);
  const meta=document.createElement("p");meta.textContent="Source : "+(method.source?.publisher||"non renseignée")+" · "+(method.source?.source_id||"identifiant non renseigné")+" · Règle : "+method.rule_id+" · Calculs : "+method.engine;details.append(meta);
  if(method.source?.url){try{const url=new URL(method.source.url);if(["https:","http:"].includes(url.protocol)&&!url.username){const link=document.createElement("a");link.href=url.href;link.rel="noopener noreferrer";link.textContent="Archive source";details.append(link);}}catch{}}
  (method.limitations||[]).forEach(t=>{const p=document.createElement("p");p.textContent=t;details.append(p);});
  (method.evidence||[]).forEach(e=>{const p=document.createElement("p");p.textContent=e.id+" — "+e.statement+" · "+e.method;details.append(p);});
  (method.claims||[]).forEach(c=>{const p=document.createElement("p");p.textContent=c.text+" — Preuves : "+c.evidence_ids.join(", ");details.append(p);});
  section.append(details);reader.append(section);
 }else{reader.append(proof);}
 title.focus();reader.scrollIntoView({block:"start"});
}
fetch("articles.json").then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{
 const articles=data.articles.filter(a=>a.status==="HUMAN_APPROVED"&&a.human_decision?.approved&&a.human_decision.draft_sha256===a.draft_sha256);
 if(!articles.length)return;
 $("#articles").replaceChildren(...articles.map(a=>{const b=document.createElement("button");b.className="article-card";const meta=document.createElement("span");meta.className="eyebrow";meta.textContent="ARTICLE · VERSION APPROUVÉE";const title=document.createElement("h3");title.textContent=a.draft.title;b.append(meta,title);b.addEventListener("click",()=>readArticle(a));return b;}));
}).catch(()=>{$("#articles").textContent="Le journal est temporairement indisponible. Merci de réessayer.";});
const context=document.modelContext;
if(context?.registerTool){
 const lifecycle=new AbortController();
 try{Promise.resolve(context.registerTool({name:"explore_pair_sum",description:"Choisir une somme dans l’expérience visible : deux nombres distincts parmi 1 à 6. Aucun tirage réel, aucune prédiction.",inputSchema:{type:"object",properties:{sum:{type:"integer",enum:[3,5,7,9,11]}},required:["sum"],additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:false},execute(input){if(!input||typeof input.sum!=="number"||Object.keys(input).some(k=>k!=="sum"))throw Error("Paramètres invalides");return selectSum(input.sum);}},{signal:lifecycle.signal})).catch(()=>{});}catch{}
 window.addEventListener("pagehide",()=>lifecycle.abort(),{once:true});
}
