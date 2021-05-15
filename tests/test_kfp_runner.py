from onceml.orchestration import KubeflowRunner,Pipeline
from components import myComponent1,myComponent2,myComponent3,myExecutor2,myExecutor1,myExecutor3
import onceml.types.channel as channel
def test_kfp_runner():
    a=myComponent1(executor=myExecutor1,a=1,b=2,resulta=channel.OutputChannel(str),resultb=channel.OutputChannel(int))
    b=myComponent2(executor=myExecutor2,inputs=[a],a=6,s=3)
    c=myComponent3(executor=myExecutor3,inputs=[a,b])
    p=Pipeline(task_name='task1',model_name='modelA',components={
        'a':a,
        'b':b,
        'c':c
    }
    )
    KubeflowRunner().deploy(pipeline=p)
if __name__ == "__main__":
    test_kfp_runner()