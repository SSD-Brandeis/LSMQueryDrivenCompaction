#include <vector>

#include "entry.h"
#include "page.h"

namespace tree_builder
{
    std::vector<Page> Page::createNewPages(int page_count)
    {
        std::vector<Page> pages(page_count);
        for (int i = 0; i < pages.size(); i++)
        {
            std::vector<Entry> entries;
            pages[i].min_sort_key = "";
            pages[i].max_sort_key = "";
            pages[i].entries_vector = entries;
        }

        return pages;
    }

}