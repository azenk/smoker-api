from datetime import datetime
import pytz

def timedelta_seconds(td):
	return td.days * 24 * 3600 + td.seconds + td.microseconds / 1000000.0

def weightedstats(data):
	stats = dict()
	datapts = len(data) - len(data) % 2
	totaltime = (data[datapts - 1][0] - data[0][0])
	totalseconds = totaltime.days * 24*3600.0 + totaltime.seconds + totaltime.microseconds / 1000000.0
	tsec = 0.0
	accum = 0.0
	stats["min"] = data[0]
	stats["max"] = data[0]

	if data[datapts - 1][1] < stats["min"][1]:
		stats["min"] = data[datapts - 1]
	if data[datapts - 1][1] > stats["max"][1]:
		stats["max"] = data[datapts - 1]

	for i in range(0,datapts-1):
		smpltime = (data[i+1][0] - data[i][0])
		seconds = smpltime.days * 24*3600.0 + smpltime.seconds + smpltime.microseconds / 1000000.0

		if data[i][1] < stats["min"][1]:
			stats["min"] = data[i]
		if data[i][1] > stats["max"][1]:
			stats["max"] = data[i]

		value = (data[i+1][1] + data[i][1])/2.0
		#print seconds,value
		accum += value*seconds
		tsec += seconds
	#print totalseconds,tsec,accum
	stats["min"] = {"time":stats["min"][0],"value":stats["min"][1]}
	stats["max"] = {"time":stats["max"][0],"value":stats["max"][1]}
	stats["avg"] = accum / tsec
	return stats


def weighted_intervals(data,interval_seconds):
	buckets = dict()
	bucketparams = dict()
	bucketparams["interval"] = interval_seconds;
	epoch = datetime(1970,1,1,tzinfo=pytz.timezone('UTC'))
	bucketparams["mintime"] = timedelta_seconds(data[0][0] - epoch)
	bucketparams["mintime"] = bucketparams["mintime"] - bucketparams["mintime"] % bucketparams["interval"]
	bucketparams["maxtime"] = timedelta_seconds(data[len(data)-1][0] - epoch)
	bucketparams["maxtime"] = bucketparams["maxtime"] - bucketparams["maxtime"] % bucketparams["interval"] + bucketparams["interval"]

	# Populate full dict of buckets
	for time in range(bucketparams["mintime"],bucketparams["maxtime"],bucketparams["interval"]):
		buckets[time] = []

	for time,value in data:
		#epoch.replace(tzinfo=time.tzinfo)
		#epoch.replace(tzinfo=None)
		#time.replace(tzinfo=None)
		unixtime = timedelta_seconds(time - epoch)
		bucket = unixtime - unixtime % bucketparams["interval"]
		if bucket not in buckets:
			buckets[bucket] = []
		buckets[bucket].append((time,value))
	avgs = []

	mintime = datetime.utcfromtimestamp(bucketparams["mintime"]).replace(tzinfo=pytz.timezone("UTC"))
	maxtime = datetime.utcfromtimestamp(bucketparams["maxtime"]).replace(tzinfo=pytz.timezone("UTC"))
	for unixtime,bucketdata in buckets.iteritems():
		start_time = datetime.utcfromtimestamp(unixtime).replace(tzinfo=pytz.timezone("UTC"))
		if start_time != mintime:
			start_value = interpolate(data,start_time)
			bucketdata.insert(0,(start_time,start_value))
		end_time = datetime.utcfromtimestamp(unixtime + bucketparams["interval"]).replace(tzinfo=pytz.timezone("UTC"))
		if end_time != maxtime:
			end_value = interpolate(data,end_time)
			bucketdata.append((end_time,end_value))
		stats = weightedstats(bucketdata)
		avgs.append({"end_time" : end_time,"avg" :  stats["avg"],"min": stats["min"],"max":stats["max"]})
	avgs.sort(lambda x,y:  1 if x["end_time"] > y["end_time"] else -1)

	return avgs
	

def interpolate(data,time):
	"""
	@data is an array of tuples (time,value) which has been sorted by time.
	@time is the time which we will interpolate a value for
	"""
	if len(data) > 1:
		# iterate over array until the index after time is found
		# TODO: replace with binary search
		if len(data) > 100:
			loopnum = 1
			if time < data[0][0]:
				i = 0
			elif time > data[len(data)-1][0]:
				i = len(data) - 1
			else:
				i = len(data) / 2**loopnum
				while (i > 0 and i <= len(data) - 1 and (data[i-1][0] > time or data[i][0] < time)):
					loopnum += 1
					step = len(data) / 2**loopnum
					if step == 0:
						step = 1

					if data[i-1][0] > time:
						i = i - step
					else:
						i = i + step

					#print data[i-1][0],data[i][0],i
					
					if i < 1:
						i = 1
	
					if i > len(data) - 1:
						i = len(data) - 1

		else:
			i = 0
			while(i < len(data) - 1 and data[i][0] < time):
				i += 1

		prior_entry = data[i-1]
		post_entry = data[i]

		value = (post_entry[1] - prior_entry[1])/timedelta_seconds(post_entry[0] - prior_entry[0]) * timedelta_seconds(time - prior_entry[0]) + prior_entry[1]
		return value
	else:
		return None
