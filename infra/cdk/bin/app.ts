#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { devConfig } from "../lib/config/dev-config";
import { DatabaseStack } from "../lib/stacks/database-stack";
import { NetworkStack } from "../lib/stacks/network-stack";

const app = new cdk.App();

const networkStack = new NetworkStack(app, "DevNetworkStack", {
  env: {
    region: devConfig.region,
  },
  applicationName: devConfig.applicationName,
  environmentName: devConfig.environmentName,
  vpcCidr: devConfig.vpcCidr,
  publicSubnets: devConfig.publicSubnets,
  privateIngressSubnets: devConfig.privateIngressSubnets,
  applicationSubnets: devConfig.applicationSubnets,
  databaseSubnets: devConfig.databaseSubnets,
});

new DatabaseStack(app, "DevDatabaseStack", {
  databaseSubnetIds: networkStack.databaseSubnetIds,
  env: {
    region: devConfig.region,
  },
  vpc: networkStack.vpc,
});

app.synth();
