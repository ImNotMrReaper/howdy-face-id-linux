import os
os.environ["OPENCV_LOG_LEVEL"] = "OFF"
os.environ["GST_DEBUG"] = "0"

import configparser
import cv2
import sys
import glob

class VideoCapture:
	def __init__(self, config):
		if isinstance(config, str):
			self.config = configparser.ConfigParser()
			self.config.read(config)
		else:
			self.config = config

		default_path = self.config.get("video", "device_path", fallback="/dev/video0")

		# Build candidate cameras in priority order: External USB cameras first, fallback to internal
		candidates = []
		try:
			by_id = "/dev/v4l/by-id"
			if os.path.isdir(by_id):
				entries = sorted(os.listdir(by_id))
				# First add index0 external cameras
				for entry in entries:
					if "Integrated" not in entry and "index0" in entry:
						p = os.path.realpath(os.path.join(by_id, entry))
						if p not in candidates and os.path.exists(p):
							candidates.append(p)
				# Then add any other video nodes for external cameras
				for entry in entries:
					if "Integrated" not in entry and "video" in entry:
						p = os.path.realpath(os.path.join(by_id, entry))
						if p not in candidates and os.path.exists(p):
							candidates.append(p)
		except Exception:
			pass

		# Ensure default fallback is in candidates
		if default_path not in candidates and os.path.exists(default_path):
			candidates.append(default_path)
		if "/dev/video0" not in candidates and os.path.exists("/dev/video0"):
			candidates.append("/dev/video0")

		self.internal = None
		self.fw = self.config.getint("video", "frame_width", fallback=-1)
		self.fh = self.config.getint("video", "frame_height", fallback=-1)
		self.force_mjpeg = self.config.getboolean("video", "force_mjpeg", fallback=False)
		self.device_path = None

		# Probe candidate cameras until one opens and grabs a frame successfully
		for candidate in candidates:
			try:
				cap = cv2.VideoCapture(candidate, cv2.CAP_V4L2)
				if self.force_mjpeg:
					cap.set(cv2.CAP_PROP_FOURCC, 1196444237)
				if self.fw != -1:
					cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.fw)
				if self.fh != -1:
					cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.fh)

				if cap.isOpened() and cap.grab():
					self.internal = cap
					self.device_path = candidate
					break
				else:
					cap.release()
			except Exception:
				continue

		if not self.internal:
			print(f"Failed to initialize any video capture device from candidates: {candidates}", file=sys.stderr)
			sys.exit(1)

	def __del__(self):
		if self.internal is not None:
			try:
				self.internal.release()
			except Exception:
				pass

	def release(self):
		if self.internal is not None:
			try:
				self.internal.release()
			except Exception:
				pass

	def read_frame(self):
		ret, frame = self.internal.read()
		if not ret:
			print("Failed to read camera frame, aborting", file=sys.stderr)
			sys.exit(1)

		try:
			gsframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		except RuntimeError:
			gsframe = frame
		except cv2.error:
			print("\nAn error occurred in OpenCV\n", file=sys.stderr)
			raise
		return frame, gsframe
