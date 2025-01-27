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
        uint32_t count = 0;
        bool value = false;
    };

    LogicFuzzer::LogicFuzzer(uint32_t seed)
    {
        std::srand(seed);
        if (pimpl_ == nullptr)
        {
            pimpl_ = new LogicFuzzerImpl();
        }
    }

    LogicFuzzer::LogicFuzzer()
    {
        LogicFuzzer(0);
    }

    LogicFuzzer::~LogicFuzzer()
    {
        if (pimpl_ != nullptr)
        {
            delete pimpl_;
        }
    }

    int LogicFuzzer::Congest()
    {
        if (pimpl_->count == 0)
        {
            pimpl_->count = std::rand() % kMaxCount;
            pimpl_->value = !pimpl_->value;
        }
        pimpl_->count--;

        return static_cast<int>(pimpl_->value);
    }
}
