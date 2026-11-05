"""Export comparison figures from saved condition CSVs, without rerunning models."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import os
os.environ.setdefault('MPLCONFIGDIR', str(Path('data/runs/matplotlib-cache').resolve()))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=Path('data/runs/comparison'))
    parser.add_argument('--output',type=Path,default=Path('docs/drosolift/evidence/p4-comparison'))
    args=parser.parse_args()
    with (args.input/'summary.csv').open(newline='',encoding='utf-8') as stream:
        rows=list(csv.DictReader(stream))
    metadata=json.loads((args.input/'results.json').read_text(encoding='utf-8'))
    loads=[.4,.8,1.2]
    colors={'recorded-neural':'#166e83','periodic':'#c56c30'}
    labels={'recorded-neural':'Recorded neural drive','periodic':'Periodic control'}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,3,figsize=(12.4,4.1))
    metrics=[('repetitions','Completed repetitions','count'),('maximum_travel','Maximum achieved travel','model distance units'),('positive_work','Positive load work','model work units')]
    for ax,(metric,title,unit) in zip(axes,metrics):
        for offset,name in [(-.17,'recorded-neural'),(.17,'periodic')]:
            values=[float(next(row[metric] for row in rows if row['condition']==name and float(row['load'])==load)) for load in loads]
            bars=ax.bar([index+offset for index in range(3)],values,width=.32,color=colors[name],label=labels[name],hatch='//' if name=='periodic' else None)
            ax.bar_label(bars,fmt='%.2g',padding=3,fontsize=9)
        ax.set(title=title,xlabel='Virtual load (model force units)',ylabel=unit,ylim=(0,None))
        ax.set_xticks(range(3),[str(load) for load in loads]); ax.margins(y=.2)
        ax.yaxis.grid(True,color='#dedede',linewidth=.6); ax.set_axisbelow(True)
    handles,legend_labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,legend_labels,loc='upper center',ncol=2,frameon=False,bbox_to_anchor=(.5,.94))
    fig.suptitle('DrosoLift: fixed-budget open-loop bench comparison',x=.055,ha='left',fontsize=14,y=.995)
    duration=float(rows[0]['duration'])
    fig.text(.055,.02,f'{duration:g}s per condition; dt={metadata["dt"]:g}s; model seed {metadata["seed"]}; separate calibration load 0.6.\nSame four-second command period and positive commanded impulse before fatigue/reflex gates. Deterministic repeats; no biological specimens.',fontsize=8,color='#414141')
    fig.subplots_adjust(left=.06,right=.99,bottom=.25,top=.78,wspace=.35)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.output.with_suffix('.png'),dpi=180,facecolor='white')
    fig.savefig(args.output.with_suffix('.svg'),facecolor='white')
    plt.close(fig)
    print(args.output.with_suffix('.png'))

if __name__=='__main__':main()
