#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/EDPutToken.h"
#include "FWCore/Utilities/interface/EDGetToken.h"

#include <chrono>
#include <thread>

namespace {
  template<typename T>
  std::vector<T> atLeastOne(std::vector<T> iV) {
    if(not iV.empty()) {
      return iV;
    }
    return std::vector<T>(1, T{0});
  }
}

namespace dune {
  class MemoryUseProd : public edm::global::EDProducer<> {
  public:
    explicit MemoryUseProd(edm::ParameterSet const&);

    void produce(edm::StreamID, edm::Event&, edm::EventSetup const&) const final;

    static void fillDescriptions(edm::ConfigurationDescriptions& descriptions);
  private:
    const std::vector<unsigned int> dataSizes_;
    const std::vector<int> uSleeps_;
    std::vector<edm::EDGetTokenT<std::vector<char>>> getTokens_;
    const edm::EDPutTokenT<std::vector<char>> putToken_;
  };

  MemoryUseProd::MemoryUseProd(edm::ParameterSet const& iPSet):
    dataSizes_(atLeastOne(iPSet.getParameter<std::vector<unsigned int>>("dataSizes"))),
    uSleeps_(atLeastOne(iPSet.getParameter<std::vector<int>>("uSleeps"))),
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

    auto id = iEvent.id().event();
    std::this_thread::sleep_for(std::chrono::milliseconds(uSleeps_[id % uSleeps_.size()]));

    iEvent.emplace(putToken_, dataSizes_[id % dataSizes_.size()], 5);
  }

  void MemoryUseProd::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
    edm::ParameterSetDescription desc;
    
    desc.add<std::vector<unsigned int>>("dataSizes", std::vector<unsigned int>(static_cast<std::size_t>(1),0U))->setComment("Amount of memory to put into each Event (in bytes). Will cycle through entries  using modulo of event number.");
    desc.add<std::vector<int>>("uSleeps", std::vector<int>(static_cast<std::size_t>(1),0))->setComment("How long to sleep for each Event, in milliseconds. Will cycle through entries using modulo of event number.");
    desc.add<std::vector<edm::InputTag>>("consume")->setComment("Which data products to consume");
  
    descriptions.addDefault(desc);
    descriptions.add("memoryUseProd", desc);
  }

}

DEFINE_FWK_MODULE(dune::MemoryUseProd);
