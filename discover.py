"""Inventaire borné de pages publiques. Aucune vidéo téléchargée."""
import argparse, hashlib, json, re, time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

ROOT=Path(__file__).resolve().parent
AGENT="RugbyTrainingLibrary/0.2"
SEEDS=[
 "https://www.rugbycoaching.tv/plans/expert/Under7s",
 "https://www.rugbycoaching.tv/videos/expert/Under8s",
 "https://www.rugbycoaching.tv/videos/expert/Under9s",
 "https://australia.rugby/participate/get-into-rugby/activities/skills-evasion",
 "https://australia.rugby/participate/get-into-rugby/club-resources/learn/run-and-evade",
 "https://australia.rugby/participate/get-into-rugby/club-resources/learn/carry-and-protect",
 "https://comiteornerugby.ffr.fr/jouer-rugby/ecoles-de-rugby/m8",
 "https://passport.world.rugby/coaching/coaching-children/putting-it-into-practice/main-coaching-activities/"
]
class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]; self.href=None; self.parts=[]; self.title=False; self.titles=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=="a":
            self.href=attrs.get("href"); self.parts=[]
        if tag=="title": self.title=True
    def handle_data(self,data):
        if self.href: self.parts.append(data)
        if self.title: self.titles.append(data)
    def handle_endtag(self,tag):
        if tag=="a":
            if self.href: self.links.append((self.href," ".join(" ".join(self.parts).split())))
            self.href=None
        if tag=="title": self.title=False

def identity(url):
    p=urlsplit(url)
    if p.hostname=="www.rugbycoaching.tv":
        match=re.search(r"/(\d{8})/?$",p.path)
        if match: return p.hostname+":"+match[1]
    return urlunsplit((p.scheme,p.netloc,p.path.rstrip("/"),p.query,""))

def relevant(url):
    p=urlsplit(url)
    return p.scheme=="https" and (
        (p.hostname=="www.rugbycoaching.tv" and re.search(r"/\d{8}/?$",p.path))
        or (p.hostname=="australia.rugby" and "/get-into-rugby/activities/" in p.path)
        or p.path.lower().endswith(".pdf"))

def get(url):
    with urlopen(Request(url,headers={"User-Agent":AGENT}),timeout=15) as r:
        raw=r.read(2_000_001)
        if len(raw)>2_000_000: raise ValueError("Page supérieure à 2 Mo")
        return raw.decode("utf-8",errors="replace")

def collect(seeds):
    found={}; journal=[]; robots={}; unavailable=set()
    for seed in seeds:
        host=urlsplit(seed).netloc
        try:
            if host in unavailable:
                journal.append({"url":seed,"status":"reporté","detail":"Hôte indisponible durant cette collecte"}); continue
            if host not in robots:
                rp=RobotFileParser()
                rp.parse(get("https://"+host+"/robots.txt").splitlines())
                robots[host]=rp
            if not robots[host].can_fetch(AGENT,seed):
                journal.append({"url":seed,"status":"robots_disallow"}); continue
            parser=Links(); page=get(seed); parser.feed(page)
            count=0
            for href,title in parser.links:
                url=urljoin(seed,href)
                if not relevant(url): continue
                p=urlsplit(url)
                if p.hostname=="www.rugbycoaching.tv":
                    url=urlunsplit((p.scheme,p.netloc,p.path,"",""))
                key=identity(url)
                if key not in found:
                    found[key]={"identity":key,"url":url,"title":title or Path(p.path).name,
                                "found_on":[],"status":"repérée — contenu à vérifier"}
                if seed not in found[key]["found_on"]: found[key]["found_on"].append(seed)
                count+=1
            journal.append({"url":seed,"status":"ok","links":count,"page_sha256":hashlib.sha256(page.encode()).hexdigest()})
        except Exception as exc:
            unavailable.add(host)
            journal.append({"url":seed,"status":"erreur","detail":str(exc)})
        time.sleep(0.5)
    return {"checked_on":date.today().isoformat(),"pages":journal,"candidates":list(found.values())}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,default=ROOT/"data/discovery.json")
    p.add_argument("--seed",action="append",help="Page de départ explicite ; remplace les pages par défaut")
    args=p.parse_args()
    result=collect(args.seed or SEEDS)
    if args.out.exists():
        previous=json.loads(args.out.read_text(encoding="utf-8"))
        merged={x["identity"]:x for x in previous["candidates"]}
        for x in result["candidates"]:
            if x["identity"] in merged:
                x["found_on"]=sorted(set(x["found_on"]+merged[x["identity"]]["found_on"]))
            merged[x["identity"]]=x
        result["candidates"]=list(merged.values())
        result["pages"]=list({x["url"]:x for x in previous["pages"]+result["pages"]}.values())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"{len(result['candidates'])} liens distincts ; "+str(sum(x["status"]=="ok" for x in result["pages"]))+" pages lues")
    for row in result["pages"]: print(row["status"],row["url"])
if __name__=="__main__": main()
