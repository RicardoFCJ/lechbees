import tkinter as tk
import serial
import time
import pandas as pd
from PIL import ImageTk, Image
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.animation as animation
import threading
import re
import numpy as np
import os

def running():
    #Animate the graph
    def animate(i):
        global cumplot
        cumplot.clear()
        vals=np.cumsum([1]*len(myData[myData.Type=="Response"]))

        valsR = []
        valsr = []
        for v in list(vals):
            if myData.Time[myData.Type=="Response"].reset_index().Time.iloc[v-1] in list(myData.Time[myData.Type=="Reinforcement"]) and not myData.Time[myData.Type=="Response"].reset_index().Time.iloc[v-1] in valsR:
                valsR.append(myData.Time[myData.Type=="Response"].reset_index().Time.iloc[v-1])
                valsr.append(v)

        cumplot.step(myData['Time'], vals,where="post")
        cumplot.scatter(myData.loc[(myData.Type=="Reinforcement")]['Time'], valsr,marker="1",s=65)
        cumplot.set_xlabel("Time in seconds")
        cumplot.set_ylabel("Responses")
    def deliver():
        var="R"
        ard.write(var.encode())

    def closing(window,subj,sess):
        global myData, stop_thread
        myData.to_csv("data/"+subj+"-"+sess+".csv",index=None, header=True)
        myData=pd.DataFrame(columns=["Subject", "Session", "Scheme", "Ratio", "Type", "Time"])
        cumplot.figure.savefig("data/"+subj+"-"+sess+".png")
        stop_thread = False
        window.destroy()

    def reinfDelivery(schema,rate,arduino,ttr,rlr,subj,sess,stTime):
        global myData, totalReinf, cumResponse, timeLastReinf
        if (schema=="FR"):
            if(str(cumResponse)==rate):
                reinf = "R"
                arduino.write(reinf.encode())
                myData = pd.concat([myData,pd.DataFrame({"Subject": [subj],"Session": [sess],"Scheme": [schema],"Ratio": [rate], "Type": ["Reinforcement"], "Time": [round(time.time()-stTime)]})],sort=False)
                totalReinf = totalReinf + 1
                ttr.set(str(totalReinf))
                cumResponse = 0
                rlr.set(str(cumResponse))
                timeLastReinf = time.time()
        elif (schema=="FI"):
            if((time.time()-timeLastReinf)>=float(rate)):
                reinf = "R"
                arduino.write(reinf.encode())
                myData = pd.concat([myData,pd.DataFrame({"Subject": [subj],"Session": [sess],"Scheme": [schema],"Ratio": [rate], "Type": ["Reinforcement"], "Time": [round(time.time()-stTime)]})],sort=False)
                totalReinf = totalReinf + 1
                ttr.set(str(totalReinf))
                cumResponse = 0
                rlr.set(str(cumResponse))
                timeLastReinf = time.time()

    def communication(arduino,subj,sess,sch,rat,stTime,tt,tlr,rlr,tr,ttr):
        global myData, lastResponse, currResponse, cumResponse, totalResponse, timeLastReinf, totalReinf, stop_thread
        myData = pd.concat([myData,pd.DataFrame({"Subject": [subj],"Session": [sess],"Scheme": [sch],"Ratio": [rat], "Type": ["Start"],"Time": [0]})],sort=False)
        lastResponse = '1'
        currResponse = '1'
        cumResponse = 0
        totalResponse = 0
        timeLastReinf = time.time()
        totalReinf = 0
        stop_thread = True

        while (stop_thread):
            values=re.findall("\d+",str(arduino.read(arduino.inWaiting())))
            tt.set(str(round(time.time() - stTime)))
            tlr.set(str(round(time.time()-timeLastReinf)))
            for i in values:
                currResponse=i
                if((currResponse=='0') and (lastResponse=='1')):
                    cumResponse = cumResponse + 1
                    rlr.set(str(cumResponse))
                    totalResponse = totalResponse + 1
                    tr.set(str(totalResponse))
                    myData = pd.concat([myData,pd.DataFrame({"Subject": [subj],"Session": [sess],"Scheme": [sch],"Ratio": [rat], "Type": ["Response"],"Time": [round(time.time()-stTime)]})],sort=False)
                    lastResponse = '0'
                    #Use this function to decide if reinforcement is delivered
                    reinfDelivery(sch,rat,arduino,ttr,rlr,subj,sess,stTime)
                elif((currResponse=='1') and (lastResponse=='0')):
                    lastResponse = '1'
            time.sleep(.5)

    if (re.search("\d+",str(re.findall("\d+",schemeValueField.get()))) is None):
        tk.messagebox.showinfo("Error:", "You must provide a value (number) to your schedule.")
    elif (re.search("\d+",str(re.findall("\d+",subjectField.get()))) is None):
        tk.messagebox.showinfo("Error:", "You must provide a value to your Subject.")
    elif (re.search("\d+",str(re.findall("\d+",sessionField.get()))) is None):
        tk.messagebox.showinfo("Error:", "You must provide a value to your Session.")
    else:
        startTime = time.time()
        t = tk.Toplevel()
        t.attributes("-fullscreen",True)
        t.wm_title("Running")
        t.configure(bg="white")

        #Graph
        global cumplot
        figure1 = plt.Figure(figsize=(6,5), dpi=100)
        cumplot = figure1.add_subplot(111)
        bar1 = FigureCanvasTkAgg(figure1, t)
        bar1.get_tk_widget().grid(column=0,row=0,columnspan=2,rowspan=6)
        cumplot.step(myData['Time'], np.cumsum([1]*len(myData)))
        ani = animation.FuncAnimation(figure1, animate, interval=500)

        #Layout
        currSessionTx = tk.Label(t, text="Current Session", font=("Arial",20),bg="white").grid(column=2,row=0,columnspan=7)
        respLastReinfTx = tk.Label(t, text="Responses since\n last reinforcer",bg="white", font=("Arial",15)).grid(column=2,row=1,columnspan=3,padx=(10,10))
        vrlr=tk.StringVar(t)
        vrlr.set("0")
        respLastReinf = tk.Label(t, textvariable=vrlr, font=("Arial",15),bg="white").grid(column=2,row=2,columnspan=3,padx=(10,10))
        timeLastReinfTx = tk.Label(t, text="Time since\n last reinforcer", font=("Arial",15),bg="white").grid(column=5,row=1,columnspan=3,padx=(10,10))
        vtlr=tk.StringVar(t)
        vtlr.set("0")
        timeLastReinf = tk.Label(t, textvariable=vtlr, font=("Arial",15),bg="white").grid(column=5,row=2,columnspan=3,padx=(10,10))
        ttResponsesTx = tk.Label(t, text="Total responses", font=("Arial",15),bg="white").grid(column=2,row=3,columnspan=2,padx=(10,10))
        vtr=tk.StringVar(t)
        vtr.set("0")
        ttResponses = tk.Label(t, textvariable=vtr, font=("Arial",15),bg="white").grid(column=2,row=4,columnspan=2,padx=(10,10))
        ttTimeTx = tk.Label(t, text="Total time", font=("Arial",15),bg="white").grid(column=4,row=3,columnspan=2,padx=(10,10))
        vtt=tk.StringVar(t)
        vtt.set("0")
        ttTime = tk.Label(t, textvariable=vtt, font=("Arial",15),bg="white").grid(column=4,row=4,columnspan=2,padx=(10,10))
        ttReinfTx = tk.Label(t, text="Total reinforcement", font=("Arial",15),bg="white").grid(column=6,row=3,columnspan=2,padx=(10,30))
        vttr=tk.StringVar(t)
        vttr.set("0")
        ttReinf = tk.Label(t, textvariable=vttr, font=("Arial",15),bg="white").grid(column=6,row=4,columnspan=2,padx=(10,10))
        tk.Button(t,
                  text='Deliver reinforecer', command=deliver, width=15, height=2, activebackground="white", bg="#006d88",bd=4).grid(row=5, column=2, columnspan=3,padx=(0,10))
        tk.Button(t,
                  text='Stop and Save', command=lambda: closing(t,subjectField.get(),sessionField.get()), width=15, height=2, activebackground="white", bg="#006d88",bd=4).grid(row=5, column=5, columnspan=3,padx=(0,10))

        #getting parameters
        porta=arduinoPar1field.get()
        baudrate=arduinoPar2field.get()

        try:
            ard=serial.Serial(porta,baudrate)
            thr = threading.Thread(target=communication,name="ComunicationThread",
                                   args=(ard,subjectField.get(),sessionField.get(),scheme.get(),schemeValueField.get(),startTime,vtt,vtlr,vrlr,vtr,vttr))

            thr.start()
            ani.start()
        #Catching this error causes the animation to not be executed
        #except AttributeError:
        #    pass
        except serial.serialutil.SerialException as e:
            tk.messagebox.showinfo("Error:", "An error occurred while trying to create the connection with Arduino. Check your Port and Baudrate parameters.\n\n"+str(e))
        #except Exception as e:
        #    tk.messagebox.showinfo("Error:", "Sorry. Something went wrong.\n\n"+str(e))

if __name__ == "__main__":
    if not (os.path.exists):
        os.makedirs('data')
    root = tk.Tk()
    root.title("LECH Bees")
    root.configure(background="white")
    #Data
    myData=pd.DataFrame(columns=["Subject", "Session", "Scheme", "Ratio", "Type", "Time"])

    logo = ImageTk.PhotoImage(Image.open("images/logo.png"))
    logoPanel = tk.Label(root, image=logo)
    logoPanel.grid(column=0, row=0,rowspan=4, columnspan=2)

    arduinoText = tk.Label(root,text="Arduino Parameters",bg="white",width=30,font=("Arial",20)).grid(column=2,row=0,columnspan=2)
    arduinoPar1 = tk.Label(root,text="Port",bg="white",font=("Arial",15)).grid(column=2,row=1)
    arduinoPar1field = tk.Entry()
    arduinoPar1field.grid(column=2,row=2)
    arduinoPar1field.insert(0,"/dev/ttyACM1")

    arduinoPar2 = tk.Label(root,text="Baudrate",bg="white",font=("Arial",15)).grid(column=3,row=1)
    arduinoPar2field = tk.Entry()
    arduinoPar2field.grid(column=3,row=2)
    arduinoPar2field.insert(0,str(9600))

    sessionText = tk.Label(root,text="Session data",bg="white",font=("Arial",20)).grid(column=0,row=4,columnspan=2,pady=(25,0))
    subjectFieldtx = tk.Label(root,text="Subject",bg="white",font=("Arial",20)).grid(column=0,row=6)
    subjectField = tk.Entry()
    subjectField.grid(column=0,row=7)
    sessionFieldtx = tk.Label(root,text="Session",bg="white",font=("Arial",20)).grid(column=1,row=6)
    sessionField = tk.Entry()
    sessionField.grid(column=1,row=7)

    reinforcementText = tk.Label(root,text="Reinforcement delivery",bg="white",font=("Arial",20)).grid(column=2,row=4,columnspan=2,pady=(25,0))
    schemeFieldtx = tk.Label(root,text="Schedule",bg="white",font=("Arial",20)).grid(column=2,row=6)
    scheme = tk.StringVar(root)
    scheme.set("FR")
    schemeField = tk.OptionMenu(root,scheme,"FR","FI")
    schemeField.grid(column=2,row=7)
    schemeValueTx = tk.Label(root,text="Value",bg="white",font=("Arial",20)).grid(column=3,row=6)
    schemeValueField = tk.Entry()
    schemeValueField.grid(column=3,row=7)

    tk.Button(root,
              text='START', command=running, width=9, height=2, activebackground="white", bg="#006d88",bd=4).grid(row=0, column=1, sticky="E",padx=(0,10))

    root.mainloop()
