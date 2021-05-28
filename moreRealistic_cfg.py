import FWCore.ParameterSet.Config as dune

#load the prototype description of the MemoryUseProd EDProducer
from DuneRawSim.Modules.memoryUseProd_cfi import memoryUseProd as _memoryUseProd

process = dune.Process("RAW")

process.source = dune.Source("EmptySource")


tasks =[]
checkClusters = []
interactionFinders =[]

deleteEarlyList = []

def generateProductName(moduleName):
    return "chars_"+moduleName+"__RAW"
def generateMightGet(moduleNames):
    return [ generateProductName(mod) for mod in moduleNames]

#create per APA modules
for x in range(1,151):
    #this module simulates reading one APA's data from storage on demand
    apaName = "apa"+str(x)
    setattr(process, "apa"+str(x), _memoryUseProd.clone(dataSizes = [40*1000*1000], consume = []))
    #want to setup to delete the memory
    deleteEarlyList.extend(generateMightGet([apaName]))

    #this module simulates timeToSpace conversion
    time2SpaceName = "time2Space"+str(x)
    setattr(process, time2SpaceName, 
            _memoryUseProd.clone( dataSizes= [40*1000*1000],
                                  consume = [apaName],
                                  uSleeps = [100],
                                  mightGet = generateMightGet([apaName])
                              ))
    deleteEarlyList.extend(generateMightGet([time2SpaceName]))

    #this module simulates finding clusters in one given APA
    clusterName = "cluster"+str(x)
    setattr(process, clusterName, 
            _memoryUseProd.clone( dataSizes= [400*1000], 
                                  consume = [time2SpaceName],
                                  uSleeps = [100],
                                  mightGet = generateMightGet([time2SpaceName])
                              ))
    deleteEarlyList.extend(generateMightGet([clusterName]))

    tasks.append( dune.Task(getattr(process,apaName), getattr(process,clusterName), getattr(process, time2SpaceName ) ) )

    #for each nearest neighbor APAs we want to create a InteractionFinder
    # which simulates handling an interaction which crosses an APA boundaries
    checkClusters.append(clusterName)
    if len(checkClusters) > 3:
        checkClusters.pop(0)
    if len(checkClusters) == 3:
        interactionFinderName="interaction"+str(x-1)
        setattr(process, interactionFinderName, 
                _memoryUseProd.clone( consume = checkClusters,
                                      dataSizes=[400*1000],
                                      mightGet = generateMightGet(checkClusters))
            )
        interactionFinders.append(interactionFinderName)

#This module looks at all APA triplets and simulates finding the best interactions
process.interactions = _memoryUseProd.clone( consume = interactionFinders,
                                             mightGet = generateMightGet(interactionFinders) )

#This simulates the time it takes to do the rest of the processing on the interactions
process.processInteraction = _memoryUseProd.clone( uSleeps = [20000],
                                                   consume = ["interactions"],
                                                   mightGet = generateMightGet(["interactions"]) )

interactionsTask = dune.Task( *(getattr(process, i) for i in interactionFinders) )
tasks.append(interactionsTask)

process.p = dune.Path(process.interactions+process.processInteraction, dune.Task(*tasks) )

#######################
#parameters to change

nThreads = 1

process.maxEvents.input = 10*nThreads
process.options.numberOfThreads = nThreads
process.options.numberOfStreams = nThreads

#delete each APA data once it is no longer needed
process.options.canDeleteEarly = deleteEarlyList

###################
#helpful for debugging

#process.out = dune.EDAnalyzer("EventContentAnalyzer")
#process.o = dune.EndPath(process.out)

#print(process.dumpPython()        )
    
#process.add_(dune.Service("Tracer"))
