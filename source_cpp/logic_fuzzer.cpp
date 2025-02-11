// Copyright (c) 2025 texer.ai. All rights reserved.
#include "logic_fuzzer.h"

// C++ libraries.
#include <cstdint>
#include <cstdlib>

namespace lf
{
    static const uint32_t kMaxCount = 16;

    struct LogicFuzzer::LogicFuzzerImpl
    {
        uint32_t count;
        bool value = false;
    };

    LogicFuzzer::LogicFuzzer(uint32_t seed)
    {
        std::srand(seed);
        pimpl_ = new LogicFuzzerImpl();
        pimpl_->count = (std::rand() % (kMaxCount - 1)) + 1;
    }

    LogicFuzzer::LogicFuzzer() : LogicFuzzer(0) { }

    LogicFuzzer::~LogicFuzzer() { delete pimpl_; }

    uint8_t LogicFuzzer::Congest() const
    {
        pimpl_->count--;

        if (pimpl_->count == 0)
        {
            pimpl_->value = !pimpl_->value;
            pimpl_->count = (std::rand() % (kMaxCount - 1)) + 1;
        }
        return static_cast<uint8_t>(pimpl_->value);
    }
}