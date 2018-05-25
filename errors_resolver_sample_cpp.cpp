#include <iostream>
#include <vector>
#include <list>

int main()
{
	std::vector<int> v = { 1 };
	std::list<int> l = { 1 };

	std::cout << v.size() << '\n';
	std::cout << l.size() << '\n';
}
