from app.entities.agent_data import AgentData, AccelerometerData
from app.entities.processed_agent_data import ProcessedAgentData


def get_road_state(
    prev_acc: AccelerometerData, 
    curr_acc: AccelerometerData
    ) -> str:

    prev_z = prev_acc.z
    curr_z = curr_acc.z
    
    smooth_threshold = 0.1  
    rough_threshold = 1.0  
    
    acc_diff = abs(curr_z - prev_z)
    if acc_diff < smooth_threshold:
        return 'smooth'
    elif acc_diff < rough_threshold:
        return 'normal'
    else:
        return 'rough'
    
    
def process_agent_data(
    agent_data: AgentData,
    prev_data: AgentData = None
) -> ProcessedAgentData:
    
    if prev_data is None:
        road_state = 'start'
    else:
        road_state = get_road_state(
            prev_data.accelerometer,
            agent_data.accelerometer
        )
        
    return ProcessedAgentData(
        road_state=road_state,
        agent_data=agent_data
    )