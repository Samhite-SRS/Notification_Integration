from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

template = Jinja2Templates("../Frontend")

app.mount("/static", StaticFiles(directory="../Frontend/static"), name="static")

#this class is a placeholder code for the database, change this later

class Notification():
    def __init__(self, recipient : str, channel : str, status  : str, created : str):
        self.recipient : str = recipient
        self.channel : str = channel
        self.status : str = status
        self.created : str = created

notifications = []

#these objects are placeholders for rows in a database
r1 = Notification("Teams", "dev-team", "pending", "18 Sep 2026")
r2 = Notification("Slack", "#engineering", "delivered", "17 Sep 2026")
r3 = Notification("Email", "example@email.com", "failed", "15 Sep 2026")

notifications.append(r1)
notifications.append(r2)
notifications.append(r3)



@app.get("/dashboard")
async def serve_dashboard(request : Request):
    #replace the context here with information from a database
    return template.TemplateResponse(name="dashboard.html", request=request,
        context={"total" : 20, "delivered" : 10,
                 "pending" : 5, "failed" : 4, "notifications" : notifications}
    )

