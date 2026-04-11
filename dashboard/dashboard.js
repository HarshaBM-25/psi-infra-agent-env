let running=false
let stepCount=0
let totalReward=0

const latHistory=[]
const rewHistory=[]

const latChart=new Chart(document.getElementById("latChart"),{
type:"line",
data:{labels:[],datasets:[{data:[],borderColor:"#4f8ef7"}]},
options:{animation:false}
})

const rewChart=new Chart(document.getElementById("rewChart"),{
type:"bar",
data:{labels:[],datasets:[{data:[],backgroundColor:"#4dbb6e"}]},
options:{animation:false}
})

async function apiGet(url){
const r=await fetch(url)
return r.json()
}

async function apiPost(url,data){
const r=await fetch(url,{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify(data)
})
return r.json()
}

async function loop(){

if(!running)return

const state=await apiGet("/state")

if(state.done){
running=false
return
}

const action={action_type:"do_nothing"}

const res=await apiPost("/step",action)

const obs=res.observation
const reward=res.reward

stepCount++
totalReward+=reward

document.getElementById("latency").innerText=Math.round(obs.avg_latency_ms)
document.getElementById("rps").innerText=Math.round(obs.requests_per_second)
document.getElementById("cpu").innerText=Math.round(obs.cpu_percent)+"%"
document.getElementById("pods").innerText=obs.active_pods
document.getElementById("score").innerText=(totalReward/stepCount).toFixed(2)

latHistory.push(obs.avg_latency_ms)
rewHistory.push(reward)

if(latHistory.length>40)latHistory.shift()
if(rewHistory.length>40)rewHistory.shift()

latChart.data.datasets[0].data=[...latHistory]
latChart.update()

rewChart.data.datasets[0].data=[...rewHistory]
rewChart.update()

renderPods(obs)

setTimeout(loop,900)

}

function renderPods(obs){

const grid=document.getElementById("pod-grid")
grid.innerHTML=""

obs.pod_statuses.forEach((s,i)=>{
const d=document.createElement("div")
d.className="pod "+s
d.innerText="P"+(i+1)
grid.appendChild(d)
})

}

async function resetSim(){

await fetch(`/reset?task_id=task1_incident_recovery&seed=42`,{method:"POST"})

stepCount=0
totalReward=0
latHistory.length=0
rewHistory.length=0

running=true
loop()

}

function setTask(task){
resetSim()
}

resetSim()