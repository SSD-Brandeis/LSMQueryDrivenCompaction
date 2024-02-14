/*
 *  Created on: May 13, 2019
 *  Author: Subhadeep
 */

#include "emu_environment.h"
#include "parse_arguments.h"
#include "run_workload.h"

int main(int argc, char *argv[]) {
  // check emu_environment.h for the contents of EmuEnv and also the definitions
  // of the singleton experimental environment
  EmuEnv *_env = EmuEnv::getInstance();
  // parse the command line arguments
  if (parse_arguments2(argc, argv, _env)) {
    exit(1);
  }

  // if (_env->verbosity >= 4) {
  //   std::cout << "printing del_per_lat" << std::endl;
  //   for (int i = 0; i < 2; ++i) {
  //     std::cout << i << ": "
  //               << EmuEnv::GetLevelDeletePersistenceLatency(i, _env)
  //               << std::endl;
  //   }
  // }

  int s = runWorkload(_env);
  return 0;
}
