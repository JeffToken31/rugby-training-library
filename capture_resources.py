"""Captures publiques locales, bornées et journalisées. Aucun téléchargement vidéo."""
import argparse
import hashlib
import json
import time
import uuid
from html.parser import HTMLParser
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.robotparser import RobotFileParser
import catalogue_v2 as v2

AGENT="RugbyTrainingLibrary/0.3"
LIMIT=5*1024*1024
def now():
    return datetime.now(timezone.utc).isoformat()
def fetch(url):
    with urlopen(Request(url,headers={"User-Agent":AGENT}),timeout=15) as response:
        data=response.read(LIMIT+1)
        if len(data)>LIMIT:
            raise ValueError("Taille maximale dépassée")
        return data,response.geturl(),response.status,response.headers.get_content_type()
def allowed(url):
    parts=urlsplit(url)
    robot=RobotFileParser()
    try:
        data,_,_,_=fetch(parts.scheme+"://"+parts.netloc+"/robots.txt")
        robot.parse(data.decode("utf-8",errors="replace").splitlines())
        delay=robot.crawl_delay(AGENT) or 0
        if delay>30:
            raise PermissionError("Temporisation robots trop longue pour ce lot")
        if not robot.can_fetch(AGENT,url):
            raise PermissionError("Accès interdit par robots.txt")
        if delay:
            time.sleep(delay)
    except HTTPError as error:
        if error.code!=404:
            raise PermissionError("Vérification robots impossible : "+str(error.code))
def capture(db,resource_id,root,refresh=False):
    source=db.execute("SELECT * FROM resources WHERE id=?",(resource_id,)).fetchone()
    if not source:
        raise ValueError("Ressource inconnue : "+resource_id)
    root=Path(root)
    # Reuse only if the actual stored bytes still match their recorded digest.
    if not refresh:
        for previous in db.execute("SELECT * FROM captures WHERE resource_id=? ORDER BY collected_at DESC",(resource_id,)):
            path=Path(previous["archive_path"])
            if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==previous["sha256"]:
                return {"resource_id":resource_id,"state":"REUSED","capture_id":previous["id"]}
    run_id=str(uuid.uuid4())
    with db:
        db.execute("INSERT INTO ingestion_runs(id,resource_id,stage,tool_version,state,started_at) VALUES(?,?,'capture','0.3','RUNNING',?)",(run_id,resource_id,now()))
    try:
        allowed(source["url"])
        data,final,status,mime=fetch(source["url"])
        if mime not in ("text/html","application/pdf","text/plain"):
            raise ValueError("Format non collecté : "+mime)
        digest=hashlib.sha256(data).hexdigest()
        root.mkdir(parents=True,exist_ok=True)
        suffix={"text/html":".html","application/pdf":".pdf","text/plain":".txt"}[mime]
        path=(root/(digest+suffix)).resolve()
        if not path.exists():
            path.write_bytes(data)
        capture_id=str(uuid.uuid4())
        with db:
            db.execute("INSERT INTO captures(id,resource_id,collected_at,final_url,http_status,mime_type,sha256,archive_path,retention_note,metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (capture_id,resource_id,now(),final,status,mime,digest,str(path),"Copie locale de travail ; pas de redistribution",json.dumps({"requested_url":source["url"],"bytes":len(data)})))
            db.execute("UPDATE ingestion_runs SET state='DONE',finished_at=?,capture_id=? WHERE id=?",(now(),capture_id,run_id))
        return {"resource_id":resource_id,"state":"DONE","capture_id":capture_id,"bytes":len(data),"mime":mime}
    except (OSError,ValueError) as error:
        state="BLOCKED" if isinstance(error,PermissionError) or isinstance(error,HTTPError) and error.code in (401,403,429) else "FAILED"
        with db:
            db.execute("UPDATE ingestion_runs SET state=?,finished_at=?,error=? WHERE id=?",(state,now(),str(error),run_id))
        return {"resource_id":resource_id,"state":state,"error":str(error)}
class TextReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ignored=0
        self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):
            self.ignored+=1
    def handle_endtag(self,tag):
        if tag in ("script","style"):
            self.ignored=max(0,self.ignored-1)
    def handle_data(self,text):
        if not self.ignored and text.strip():
            self.parts.append(text.strip())
def extract_html(db,capture_id):
    row=db.execute("SELECT * FROM captures WHERE id=?",(capture_id,)).fetchone()
    if row["mime_type"]!="text/html":
        return
    path=Path(row["archive_path"])
    reader=TextReader()
    reader.feed(path.read_text(encoding="utf-8",errors="replace"))
    output=path.with_suffix(".text.txt")
    output.write_text("\n".join(reader.parts),encoding="utf-8")
    with db:
        db.execute("UPDATE captures SET raw_text_path=?,extractor_version='html-text-0.1' WHERE id=?",(str(output),capture_id))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("resources",nargs="+")
    p.add_argument("--db",type=Path,default=v2.ROOT/"data/rugby-v2.sqlite")
    p.add_argument("--raw",type=Path,default=v2.ROOT/"data/raw")
    p.add_argument("--refresh",action="store_true")
    a=p.parse_args()
    blocked_hosts=set()
    with v2.connect(a.db) as db:
        for id in a.resources:
            row=db.execute("SELECT url FROM resources WHERE id=?",(id,)).fetchone()
            if not row:
                print(json.dumps({"resource_id":id,"state":"FAILED","error":"Ressource inconnue"}))
                continue
            host=urlsplit(row[0]).netloc
            if host in blocked_hosts:
                print(json.dumps({"resource_id":id,"state":"SKIPPED","error":"Hôte déjà bloqué dans ce lot"}))
                continue
            result=capture(db,id,a.raw,a.refresh)
            if result["state"] in ("DONE","REUSED"):
                extract_html(db,result["capture_id"])
            if result["state"]=="BLOCKED":
                blocked_hosts.add(host)
            print(json.dumps(result,ensure_ascii=False),flush=True)
            time.sleep(0.5)
if __name__=="__main__":
    main()
