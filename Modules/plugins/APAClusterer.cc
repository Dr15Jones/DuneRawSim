#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/EDPutToken.h"
#include "FWCore/Utilities/interface/EDGetToken.h"

#include <chrono>
#include <thread>

namespace dune {
  class APAClusterer : public edm::global::EDProducer<> {
  public:
    explicit APAClusterer(edm::ParameterSet const&);

    void produce(edm::StreamID, edm::Event&, edm::EventSetup const&) const final;

  private:
    const size_t dataSize_;
    int milliSecSleep_=100;
    const edm::EDGetTokenT<std::vector<char>> getToken_;
    const edm::EDPutTokenT<std::vector<float>> putToken_;

  };

  APAClusterer::APAClusterer(edm::ParameterSet const& iPSet):
    dataSize_(iPSet.getParameter<unsigned int>("dataSize")),
    getToken_(consumes<std::vector<char>>(iPSet.getParameter<edm::InputTag>("apa"))),
    putToken_(produces<std::vector<float>>())
  {}

  void APAClusterer::produce(edm::StreamID,edm::Event& iEvent, edm::EventSetup const&) const 
  {
    (void) iEvent.get(getToken_);

    std::this_thread::sleep_for(std::chrono::milliseconds(milliSecSleep_));

    iEvent.emplace(putToken_, dataSize_/sizeof(float), 3.14);
  }
}

DEFINE_FWK_MODULE(dune::APAClusterer);
