#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/EDPutToken.h"
#include "FWCore/Utilities/interface/EDGetToken.h"

#include <chrono>
#include <thread>

namespace dune {
  class MemoryUseProd : public edm::global::EDProducer<> {
  public:
    explicit MemoryUseProd(edm::ParameterSet const&);

    void produce(edm::StreamID, edm::Event&, edm::EventSetup const&) const final;

    static void fillDescriptions(edm::ConfigurationDescriptions& descriptions);
  private:
    const size_t dataSize_;
    const int milliSecSleep_;
    std::vector<edm::EDGetTokenT<std::vector<char>>> getTokens_;
    const edm::EDPutTokenT<std::vector<char>> putToken_;
  };

  MemoryUseProd::MemoryUseProd(edm::ParameterSet const& iPSet):
    dataSize_(iPSet.getParameter<unsigned int>("dataSize")),
    milliSecSleep_(iPSet.getParameter<int>("uSleep")),
    putToken_(produces<std::vector<char>>())
  {
    for(auto const& tag: iPSet.getParameter<std::vector<edm::InputTag>>("consume")) {
      getTokens_.emplace_back(consumes(tag));
    }
  }

  void MemoryUseProd::produce(edm::StreamID,edm::Event& iEvent, edm::EventSetup const&) const 
  {
    for(auto const& token: getTokens_) {
      (void) iEvent.get(token);
    }

    std::this_thread::sleep_for(std::chrono::milliseconds(milliSecSleep_));

    iEvent.emplace(putToken_, dataSize_, 5);
  }

  void MemoryUseProd::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    
    desc.add<unsigned int>("dataSize", 0)->setComment("Amount of memory to put into Event (in bytes)");
    desc.add<int>("uSleep", 0)->setComment("How long to sleep, in milliseconds");
    desc.add<std::vector<edm::InputTag>>("consume")->setComment("Which data products to consume");
  
    descriptions.addDefault(desc);
    descriptions.add("memoryUseProd", desc);
  }

}

DEFINE_FWK_MODULE(dune::MemoryUseProd);
