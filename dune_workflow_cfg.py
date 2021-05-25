import FWCore.ParameterSet.Config as dune

process = dune.Process("RAW")

process.source = dune.Source("EmptySource")


tasks =[]
checkClusters = []
interactionFinders =[]

deleteEarlyList = []

#create per APA modules
for x in range(1,151):
    #this module simulates reading one APA's data from storage on demand
    apaName = "apa"+str(x)
    setattr(process, "apa"+str(x), dune.EDProducer("dune::APAGenerator",dataSize=dune.uint32(40*1000*1000)))
    apaProduct = "chars_"+apaName+"__RAW"
    deleteEarlyList.append(apaProduct)

    #this module simulates finding clusters in one given APA
    clusterName = "cluster"+str(x)
    setattr(process, clusterName, dune.EDProducer("dune::APAClusterer", 
                                                  dataSize=dune.uint32(400*1000), 
                                                  apa = dune.InputTag(apaName),
                                                  mightGet = dune.untracked.vstring(apaProduct)
                                              ))

    tasks.append( dune.Task(getattr(process,apaName), getattr(process,clusterName) ) )

    #for each nearest neighbor APAs we want to create a InteractionFinder
    # which simulates handling an interaction which crosses an APA boundaries
    checkClusters.append(clusterName)
    if len(checkClusters) > 3:
        checkClusters.pop(0)
    if len(checkClusters) == 3:
        interactionFinderName="interaction"+str(x-1)
        setattr(process, interactionFinderName, 
                dune.EDProducer("dune::InteractionFinder", 
                                apaClusters = dune.VInputTag((dune.InputTag(x) for x in checkClusters)) ) )
        interactionFinders.append(interactionFinderName)

#This module looks at all APA triplets and simulates finding the best interactions
process.interactions = dune.EDProducer("dune::InteractionAccumulator",
                                    interactions = dune.VInputTag((dune.InputTag(x) for x in interactionFinders)))

#This simulates the time it takes to do the rest of the processing on the interactions
process.processInteraction = dune.EDProducer("dune::InteractionProcessor",
                                             uSleep = dune.untracked.int32(20000),
                                  interactions = dune.InputTag("interactions"))

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
