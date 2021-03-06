#include "ros/ros.h"
#include "std_msgs/Header.h"
#include "sensor_msgs/Image.h"
#include "geometry_msgs/Pose.h"

#include "visp_bridge/image.h"
#include <visp/vpImageIo.h>
#include <visp/vpDisplayX.h>
#include <visp/vpMeLine.h>
#include <visp/vpTemplateTracker.h>
#include <visp/vpTemplateTrackerSSDESM.h>
#include <visp/vpTemplateTrackerSSDForwardAdditional.h>
#include <visp/vpTemplateTrackerSSDForwardCompositional.h>
#include <visp/vpTemplateTrackerSSDInverseCompositional.h>
#include <visp/vpTemplateTrackerZNCCForwardAdditional.h>
#include <visp/vpTemplateTrackerZNCCInverseCompositional.h>
#include <visp/vpTemplateTrackerWarpHomography.h>
#include <visp/vpTrackingException.h>

#include "detector/landing_mark_detection.h"

#include "detectortracker.h"
#include "mark_tracker.h"
#include "mbtracker.h"

#include <time.h>

ros::Publisher roiPub;
ros::Publisher posePub;
ros::Publisher filteredPosePub;

DetectorTracker * detectorTracker;

bool use_mbt;

void imageCallback(const sensor_msgs::Image::ConstPtr& msg)
{
  clock_t start, end;
  //ROS_INFO("Image Recevied, %d %d %d", msg->header.seq, msg->width, msg->height);
  start = clock();
  detectorTracker->detectAndTrack(msg);
  end = clock();
  //ROS_INFO("detectorTracker took %f seconds", ((float)(end - start))/CLOCKS_PER_SEC);
  sensor_msgs::RegionOfInterest data = detectorTracker->getRegionOfInterest();
  roiPub.publish(data);
  if(use_mbt){
	posePub.publish(dynamic_cast<TrackMarkerModel*>(detectorTracker)->getPoseStamped());
	filteredPosePub.publish(dynamic_cast<TrackMarkerModel*>(detectorTracker)->getPoseStamped());
  }
}

// Reads params, or sets default parameters if parameters are not found
void readParams(int& camSizeX, int& camSizeY, bool& use_mbt, int& trackerType,
				std::string& camTopic, std::string& pubTopic, std::string& poseTopic,
				std::string& filteredPoseTopic)
{
  if(!(ros::param::get("/visptracker/cam_resolution_x", camSizeX) && 
	 ros::param::get("/visptracker/cam_resolution_y", camSizeY)))
  {
	ROS_WARN("Cannot find camera resolution params cam_resolution_x or cam_resolution_y");
	camSizeX = 1920;
	camSizeY = 1080;
  }
  ROS_INFO("Set camera resolution to %d %d", camSizeX, camSizeY);
  
  if(!ros::param::get("/visptracker/use_mbt", use_mbt))
  {
	ROS_WARN("Cannot read use_mbt parameter.");
	use_mbt = true;
  }
  ROS_INFO("Tracker will %suse model-based tracking", (use_mbt ? "" : "NOT "));

  if(ros::param::get("/visptracker/tracker_type", trackerType) && (trackerType < 0 || trackerType > 5))
  {
	ROS_WARN("Cannot read valid tracker type parameter");
	trackerType = 1;
  }
  ROS_INFO("Set tracker type to %d", trackerType);

  if(!ros::param::get("/visptracker/cam_topic", camTopic))
  {
	ROS_WARN("Cannot get cam_topic string parameter");
	camTopic = "/ardrone/downward_cam/camera/image";
  }
  ROS_INFO("Set camera topic to %s", camTopic.c_str());

  
  if(!ros::param::get("/visptracker/pub_topic", pubTopic))
  {
	ROS_WARN("Cannot get publisher topic string parameter");
	pubTopic = "visptracker_data";
  }
  ROS_INFO("Set publisher topic name as %s", pubTopic.c_str());

  if(!ros::param::get("/visptracker/pose_topic", poseTopic))
  {
	ROS_WARN("Cannot get pose topic string parameter");
	poseTopic = "visptracker_pose";
  }
  ROS_INFO("Set pose topic name as %s", poseTopic.c_str());

  if(!ros::param::get("/visptracker/pose_topic_filtered", filteredPoseTopic))
  {
	ROS_WARN("Cannot get filtered pose topic string parameter");
	filteredPoseTopic = "visptracker_pose_filtered";
  }
  ROS_INFO("Set filtered pose topic name as %s", filteredPoseTopic.c_str());
}

int main(int argc, char ** argv)
{
  ros::init(argc, argv, "visptracker");
  ros::NodeHandle n;
  
  // read parameters first
  int camSizeX, camSizeY, trackerType;
  std::string camTopic, pubTopic, poseTopic, filteredPoseTopic;
  ROS_INFO("Reading parameters...");
  readParams(camSizeX, camSizeY, use_mbt, trackerType, camTopic, pubTopic, poseTopic, filteredPoseTopic);
  ROS_INFO("Parameters loaded successfully!");

  if(use_mbt){
	TrackMarkerModel * tmm = new TrackMarkerModel(camSizeX, camSizeY);
	tmm->setMaskSize(5);
	tmm->setMaskNumber(180);
	tmm->setRange(30);
	tmm->setThreshold(50000);
	tmm->setMu1(0.5);
	tmm->setMu2(0.5);
	tmm->setSampleStep(4);
	detectorTracker = tmm;
  }else{
	TrackLandingMark * tlm = new TrackLandingMark(camSizeX, camSizeY, (TrackerType)trackerType);
	tlm->setSampling(4, 4);
	tlm->setLambda(0.001);
	tlm->setIterationMax(50);
	tlm->setPyramidal(4, 2);
	detectorTracker = tlm;
  }

  ros::Subscriber sub = n.subscribe(camTopic, 1, imageCallback);
  roiPub = n.advertise<sensor_msgs::RegionOfInterest>(pubTopic, 1000);
  posePub = n.advertise<geometry_msgs::PoseStamped>(poseTopic, 1000);
  filteredPosePub = n.advertise<geometry_msgs::PoseStamped>(filteredPoseTopic, 1000);

  detectorTracker->enableTrackerDisplay(true);
  
  ros::spin();
   
  return 0;
}
