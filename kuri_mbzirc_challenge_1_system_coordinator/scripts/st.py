#!/usr/bin/env python

import roslib; 
import rospy
import actionlib
import smach
import smach_ros
import time
from std_msgs.msg import String
from sensor_msgs.msg import RegionOfInterest
from geometry_msgs.msg import PoseStamped
import kuri_mbzirc_challenge_1_msgs.msg
from kuri_mbzirc_challenge_1_msgs.srv import PES 
from kuri_msgs.msg import Object

xPose = 0 
yPose = 0 
zPose = 0 

# define state : exploration
class exploration(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['StayInExploration' , 'Move2Landing'])
        self.end_mission_sub = rospy.Subscriber('/endMission', String, self.missionCallback)
        self.start_mission_pub = rospy.Publisher('/startMission' , String, queue_size=10)
        self.goal_pub = rospy.Publisher('/kuri_offboard_attitude_control_test/goal' , PoseStamped, queue_size=1)
        self.pose_sub = rospy.Subscriber('/mavros/local_position/pose', PoseStamped, self.localPoseCallback);
        self.tracked = False 

    def localPoseCallback(self, topic):
      xPose = topic.pose.position.x 
      yPose = topic.pose.position.y
      zPose = topic.pose.position.z 


    def missionCallback(self , topic):
	if topic.data == 'reachedCenter':
		self.tracked = True
	else: 
		self.tracked = False 


    def execute(self, userdata):
      	msg1 = "startMission" 
        self.start_mission_pub.publish(msg1)
        if self.tracked == True:	      
	      self.tracked = False 
	      msg2a = PoseStamped() 
	      msg2a.pose.position.x = xPose 
	      msg2a.pose.position.y = yPose
	      msg2a.pose.position.z = zPose
	      self.goal_pub.publish(msg2a)
	      return 'Move2Landing'
	else: 
 	    print "moveWAYPOINT " 
 	    msg2 = PoseStamped() 
 	    msg2.pose.position.x =  0 
	    msg2.pose.position.y =  0 
	    msg2.pose.position.z =  10 
	    self.goal_pub.publish(msg2)
	    return 'StayInExploration' 
       

# define state : marker_detection
class trajectory_following(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['Move2Docking','StayInLanding'])
        self.goal_pub = rospy.Publisher('/kuri_offboard_attitude_control_test/goal' , PoseStamped, queue_size=1)
        self.end_mission_sub = rospy.Subscriber('/endMission', String, self.missionCallback)
        self.start_mission_pub = rospy.Publisher('/startMission' , String, queue_size=1)
        self.box_sub = rospy.Subscriber('/ch1/marker_bb', RegionOfInterest, self.boxCallback)
        self.pose_sub = rospy.Subscriber('/mavros/local_position/pose', PoseStamped, self.localPoseCallback);
	self.resp1 = Object() 
	self.res = PoseStamped () 
        self.a = 0 
        self.b = 0 
	self.moveToDocking = False 

    def localPoseCallback(self, topic):
      xPose = topic.pose.position.x 
      yPose = topic.pose.position.y
      zPose = topic.pose.position.z 


    def missionCallback(self , topic):
	if topic.data == "Landed":
		self.moveToDocking = True 
	else:
		self.moveToDocking = False

    def boxCallback(self , topic):
        print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$"
        print "toopic DATA" , topic.x_offset 
        print "toopic DATA" , topic.y_offset 

	self.a = topic.x_offset + (topic.width/2.0)
	self.b = topic.y_offset + (topic.height/2.0)
        print "self.a" , self.a 
        print "self.b" , self.b
        client = rospy.ServiceProxy('position_estimation', PES)
	self.resp1 = client(self.a, self.b)
	self.res.pose.position.x = self.resp1.obj.pose.pose.position.x
	print "*****************************************"
	print "Obj X" , self.resp1.obj.pose.pose.position.x  
	print "Obj Y" , self.resp1.obj.pose.pose.position.y
		
    def execute(self, userdata):
        msg3 = "startLanding" 
        self.start_mission_pub.publish(msg3)
        rospy.loginfo('Executing state TRAJECTORY_FOLLOWING')
        time.sleep(2)
        if self.moveToDocking == True:
	    msg4a = PoseStamped() 
	    msg4a.pose.position.x = xPose 
	    msg4a.pose.position.y = yPose
	    msg4a.pose.position.z =  zPose
	    self.goal_pub.publish(msg4a)
	    self.moveToDocking = False
            return 'Move2Docking'
	    
        else: 
	    #ROS_INFO("poseX: %ld", resp1.obj.pose.pose.position.x);
	    #ROS_INFO("poseY: %ld", resp1.obj.pose.pose.position.y);
	    #ROS_INFO("poseZ: %ld", resp1.obj.pose.pose.position.z);
	    if (self.res.pose.position.x > 0 or self.res.pose.position.x < 0 or self.res.pose.position.x  ==0 ):
	      msg4 = PoseStamped( ) 
	      msg4.pose.position.x = self.resp1.obj.pose.pose.position.x 
	      msg4.pose.position.y = self.resp1.obj.pose.pose.position.y
	      msg4.pose.position.z =  2
              self.moveToDocking = False
	      self.goal_pub.publish(msg4)
	      return 'StayInLanding'
	    else:
	      msg4b = PoseStamped( ) 
	      msg4b.pose.position.x = xPose 
	      msg4b.pose.position.y = yPose
	      msg4b.pose.position.z = zPose + 5.0
	      self.goal_pub.publish(msg4b)
              self.moveToDocking = False
	      return 'StayInLanding'
	      
	  
# define state : docking
class docking(smach.State):
    def __init__(self):
        smach.State.__init__(self, outcomes=['docking','docked'])
        self.goal_pub = rospy.Publisher('/kuri_offboard_attitude_control_test/goal' , PoseStamped, queue_size=1)
        self.end_mission_sub = rospy.Subscriber('/endMission', String, self.missionCallback)
        self.start_mission_pub = rospy.Publisher('/startMission' , String, queue_size=10)
        self.moveToEnd = False
	#self.counter=0

    def missionCallback(self , topic):
	if topic.data == "Docked":
		self.moveToDocking = True 
	else:
		self.moveToDocking = False
		
    def execute(self, userdata):
        msg5 = "startDocking" 
        self.start_mission_pub.publish(msg5)
        rospy.loginfo('Executing state DOCKING')
        time.sleep(2)
        if self.moveToEnd == False:
	        msg6= PoseStamped() 
	   	msg6.pose.position.x =  0 
		msg6.pose.position.y =  0 
		msg6.pose.position.z =  1.5 
		self.goal_pub.publish(msg6)
                return 'docking'
        else: 
        	return 'docked'

# main
class Challenge1():
	rospy.init_node('MBZIRC_ch1_state_machine')
 	# Create a SMACH state machine
	sm = smach.StateMachine(outcomes=['Done'])

	with sm: 
		# add states to the container 
		#smach.StateMachine.add('INIT', Initilization(),
                 #               transitions={'start':'EXPLORATION'})

		smach.StateMachine.add('EXPLORATION', exploration(),
                                transitions={'StayInExploration':'EXPLORATION',
                                             'Move2Landing':'TRAJECTORY_FOLLOWING'})


		smach.StateMachine.add('TRAJECTORY_FOLLOWING', trajectory_following(),
                                transitions={'Move2Docking':'DOCKING',
                                             'StayInLanding':'TRAJECTORY_FOLLOWING'})

		smach.StateMachine.add('DOCKING', docking(),
                                transitions={'docking':'DOCKING',
                                             'docked':'Done'})


	sis = smach_ros.IntrospectionServer('server_name', sm, '/SM_ROOT')
        sis.start()

        # Execute SMACH plan
        outcome = sm.execute()
        rospy.spin()
        sis.stop()



if __name__ == '__main__':
	Challenge1()
